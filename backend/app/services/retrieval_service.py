"""
Retrieval layer for the copilot: the two halves of hybrid GraphRAG.

  - vector_search: semantic passages from Qdrant (the document side)
  - resolve_equipment_in_query / gather_graph_context: structured facts from the
    graph via the services we already built (the knowledge side)

The copilot combines both. Keeping retrieval here means copilot_service stays
about reasoning, not about how to talk to Qdrant or which Cypher to run.
"""

from pydantic import BaseModel, Field
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from app.config import settings
from app.db.qdrant_client import get_qdrant
from app.ingestion.extractors.base import find_equipment_tags
from app.services.embeddings import embed_query
from app.services.equipment_service import DocumentLink, TimelineItem, get_equipment_360
from app.services.prediction_service import PredictionResult, get_predictions

# The plant's real assets, parsed once. Used to keep query resolution honest.
KNOWN_EQUIPMENT = {t.strip() for t in settings.KNOWN_EQUIPMENT.split(",") if t.strip()}


class ChunkHit(BaseModel):
    text: str
    doc_id: str | None = None
    source: str | None = None
    chunk_index: int | None = None
    score: float | None = None


class GraphContext(BaseModel):
    tag: str
    name: str | None = None
    type: str | None = None
    health_line: str = ""
    prediction: PredictionResult | None = None
    timeline: list[TimelineItem] = Field(default_factory=list)
    documents: list[DocumentLink] = Field(default_factory=list)
    doc_ids: list[str] = Field(default_factory=list)


def vector_search(
    query: str,
    equipment_tag: str | None = None,
    doc_ids: list[str] | None = None,
    top_k: int = 6,
) -> list[ChunkHit]:
    """
    Semantic search over document chunks.

    When we know the asset, we bias retrieval towards it: a chunk qualifies if it
    is tagged with the asset OR belongs to a document the graph links to that
    asset (its manual, its regulations). That second path matters because generic
    manuals carry no equipment tag in their payload, so a tag-only filter would
    miss exactly the lubrication or spec passages we want.
    """
    vector = embed_query(query)

    should = []
    if equipment_tag:
        should.append(FieldCondition(key="equipment_tags", match=MatchValue(value=equipment_tag)))
    if doc_ids:
        should.append(FieldCondition(key="doc_id", match=MatchAny(any=list(doc_ids))))
    query_filter = Filter(should=should) if should else None

    hits = get_qdrant().search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )
    return [
        ChunkHit(
            text=h.payload.get("text", ""),
            doc_id=h.payload.get("doc_id"),
            source=h.payload.get("source"),
            chunk_index=h.payload.get("chunk_index"),
            score=h.score,
        )
        for h in hits
    ]


def resolve_equipment_in_query(query: str) -> str | None:
    """Return the first known asset tag named in the question, else None."""
    # Upper-case first so "what's wrong with p-101?" still resolves.
    for tag in find_equipment_tags(query.upper()):
        if tag in KNOWN_EQUIPMENT:
            return tag
    return None


def gather_graph_context(tag: str) -> GraphContext | None:
    """
    Compact, LLM-ready facts about one asset, drawn from the existing services.

    Deliberately small: the six most recent timeline events, the linked documents,
    and the current prediction. The goal is to hand the model trustworthy facts to
    reason over, not to dump the whole subgraph.
    """
    bio = get_equipment_360(tag)
    if bio is None:
        return None

    h = bio.health
    health_line = (
        f"{h.total_work_orders} work orders ({h.open_work_orders} open), "
        f"{h.incident_count} incident(s), last activity {h.last_work_order_date}."
    )
    predictions = [p for p in get_predictions(tag) if p.status == "predicted"]

    return GraphContext(
        tag=bio.summary.tag,
        name=bio.summary.name,
        type=bio.summary.type,
        health_line=health_line,
        prediction=predictions[0] if predictions else None,
        timeline=bio.timeline[:6],
        documents=bio.documents,
        doc_ids=[d.doc_id for d in bio.documents],
    )
