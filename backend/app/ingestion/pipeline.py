"""
The ingestion pipeline: run all six stages for a file and report what happened.

    extract_text -> entities -> relationships -> graph merge -> chunk -> embed

`ingest_file` handles one document; `ingest_directory` walks the whole corpus for
seeding the demo. Both return summaries (counts, warnings) rather than raising on
a single bad file, so a bulk seed keeps going and tells you what it did.
"""

import logging
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import settings
from app.ingestion.chunking import chunk_text
from app.ingestion.embedding import embed_and_store
from app.ingestion.entity_extraction import (
    EquipmentEntity,
    ExtractedEntities,
    extract_entities,
    work_orders_from_table,
)
from app.ingestion.extractors.base import ExtractedContent
from app.ingestion.graph_merge import merge_document_graph
from app.ingestion.relationship_extraction import build_relationships
from app.ingestion.text_extraction import extract_text

logger = logging.getLogger(__name__)

# The plant's real asset tags. Anything outside this set is a false-positive match
# from a generic manual/regulation and must not become an Equipment node.
KNOWN_EQUIPMENT = {t.strip() for t in settings.KNOWN_EQUIPMENT.split(",") if t.strip()}


class IngestSummary(BaseModel):
    file: str
    doc_id: str
    doc_type: str
    entity_counts: dict[str, int] = Field(default_factory=dict)
    nodes_total: int = 0
    nodes_created: int = 0
    nodes_merged: int = 0
    relationships_written: int = 0
    chunks_embedded: int = 0
    warnings: list[str] = Field(default_factory=list)


class DirectorySummary(BaseModel):
    root: str
    files_ingested: int = 0
    files_failed: int = 0
    nodes_created: int = 0
    chunks_embedded: int = 0
    per_file: list[IngestSummary] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def ingest_file(path: str | Path, embed: bool = True) -> IngestSummary:
    """Run the full pipeline on one file. `embed=False` skips the vector step (tests)."""
    path = Path(path)
    content = extract_text(path)
    doc_meta = _build_doc_meta(path, content)

    entities = _entities_for(content)
    relationships = build_relationships(entities, doc_meta["doc_id"])
    graph = merge_document_graph(doc_meta, entities, relationships)

    chunks_embedded = 0
    if embed:
        chunks = chunk_text(content.text)
        chunks_embedded = embed_and_store(chunks, _chunk_metadata(doc_meta, entities))

    return IngestSummary(
        file=path.name,
        doc_id=doc_meta["doc_id"],
        doc_type=content.doc_type,
        entity_counts=_entity_counts(entities),
        nodes_total=graph["nodes_total"],
        nodes_created=graph["nodes_created"],
        nodes_merged=graph["nodes_merged"],
        relationships_written=graph["relationships_written"],
        chunks_embedded=chunks_embedded,
        warnings=content.warnings,
    )


def ingest_directory(root: str | Path | None = None, embed: bool = True) -> DirectorySummary:
    """Ingest every supported file under a folder (used to seed the demo)."""
    root = Path(root or settings.DATA_DIR)
    summary = DirectorySummary(root=str(root))

    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            result = ingest_file(path, embed=embed)
        except ValueError as exc:
            # Unsupported file type; note it and move on.
            summary.errors.append(f"{path.name}: {exc}")
            continue
        except Exception as exc:  # keep the seed going even if one file misbehaves
            logger.exception("Ingest failed for %s", path)
            summary.files_failed += 1
            summary.errors.append(f"{path.name}: {exc}")
            continue

        summary.per_file.append(result)
        summary.files_ingested += 1
        summary.nodes_created += result.nodes_created
        summary.chunks_embedded += result.chunks_embedded

    return summary


def _entities_for(content: ExtractedContent) -> ExtractedEntities:
    """Choose the extraction path by document type, then keep only real assets."""
    if content.doc_type == "workorders":
        rows = [row for table in content.tables for row in table]
        entities = work_orders_from_table(rows)
    elif content.doc_type == "pid":
        # The drawing's tags are the reliable signal; make an Equipment entity per tag.
        entities = ExtractedEntities(equipment=[EquipmentEntity(tag=t) for t in content.equipment_tags])
    else:
        entities = extract_entities(content.text, known_tags=content.equipment_tags)
        _ensure_literal_tags(entities, content.equipment_tags)

    return _keep_known_equipment(entities)


def _keep_known_equipment(entities: ExtractedEntities) -> ExtractedEntities:
    """
    Drop equipment (and equipment references) that are not in the asset register.
    Keeps the graph to real plant assets instead of stray tag-like strings.
    """
    entities.equipment = [e for e in entities.equipment if e.tag in KNOWN_EQUIPMENT]
    entities.work_orders = [w for w in entities.work_orders if w.equipment_tag in KNOWN_EQUIPMENT]
    for i in entities.incidents:
        if i.equipment_tag not in KNOWN_EQUIPMENT:
            i.equipment_tag = None
    for f in entities.failure_modes:
        if f.equipment_tag not in KNOWN_EQUIPMENT:
            f.equipment_tag = None
    return entities


def _ensure_literal_tags(entities: ExtractedEntities, tags: list[str]) -> None:
    """Guarantee any tag literally present in the text becomes an Equipment node."""
    known = {e.tag for e in entities.equipment}
    for tag in tags:
        if tag not in known:
            entities.equipment.append(EquipmentEntity(tag=tag))


def _build_doc_meta(path: Path, content: ExtractedContent) -> dict:
    """Document node properties, including versioning metadata for later use."""
    return {
        "doc_id": path.stem,  # filenames in this corpus are unique and stable
        "title": path.stem.replace("_", " "),
        "type": content.doc_type,
        "version": "1",
        "upload_date": date.today().isoformat(),
        "source": path.name,
    }


def _chunk_metadata(doc_meta: dict, entities: ExtractedEntities) -> dict:
    """Payload stored with every chunk so it traces back to equipment and document."""
    tags = [e.tag for e in entities.equipment]
    return {
        "doc_id": doc_meta["doc_id"],
        "source": doc_meta["source"],
        "doc_type": doc_meta["type"],
        "upload_date": doc_meta["upload_date"],
        "equipment_tags": tags,
        "equipment_tag": tags[0] if tags else None,  # primary tag for quick filtering
    }


def _entity_counts(e: ExtractedEntities) -> dict[str, int]:
    return {
        "equipment": len(e.equipment),
        "people": len(e.people),
        "incidents": len(e.incidents),
        "work_orders": len(e.work_orders),
        "regulations": len(e.regulations),
        "failure_modes": len(e.failure_modes),
    }
