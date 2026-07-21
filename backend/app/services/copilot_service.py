"""
The Expert Copilot: answers plant questions from retrieved evidence, always cited.

Flow for one question:
  resolve the asset -> gather its graph facts -> retrieve document passages ->
  build one grounded prompt (facts + passages, each with a citable label) ->
  ask the LLM to answer only from that context and name the labels it used ->
  map those labels back to structured citations.

The model never sees the raw graph or free web; it only sees the labelled context
we assembled, so every claim it makes can be traced to a source. When the context
does not cover the question, the prompt requires it to say so instead of guessing.
"""

from pydantic import BaseModel, Field

from app.services.llm import complete_json_verbose
from app.services.retrieval_service import (
    ChunkHit,
    GraphContext,
    gather_graph_context,
    resolve_equipment_in_query,
    vector_search,
)

_SYSTEM = (
    "You are SANJEEVANI, an expert assistant for the Bharat Petrochem Unit-2 refinery. "
    "Answer ONLY from the GRAPH FACTS and DOCUMENT PASSAGES provided. Write like a "
    "knowledgeable plant engineer: direct and practical. Cite every factual claim using "
    "the bracketed source labels (for example WO-1041, INC-2023-41, D1, PREDICTION). "
    "If the provided context does not contain the answer, say you do not have enough "
    "information and cite nothing. Never invent part numbers, dates, clause numbers, or "
    "any fact that is not in the context. "
    'Respond as JSON: {"answer": "...", "citations": ["<label>", ...]}.'
)


class Citation(BaseModel):
    type: str  # workorder | incident | document | prediction
    ref: str  # wo_id / incident id / doc_id / equipment tag
    title: str | None = None
    snippet: str | None = None
    equipment_tag: str | None = None  # link target for the frontend, when relevant
    # Only present where we have a real number: the Qdrant similarity for a
    # retrieved passage. Graph facts have no comparable score, so we leave it None
    # rather than invent one.
    score: float | None = None


# Structured graph evidence is listed before supporting document passages. This
# is the "principled ordering" without fabricating per-citation confidence.
_TYPE_PRIORITY = {"prediction": 0, "incident": 1, "workorder": 2, "document": 3}


class CopilotAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    resolved_equipment: str | None = None
    context_used: dict = Field(default_factory=dict)  # for a debug/expand view
    usage: dict = Field(default_factory=dict)  # token counts for cost tracking


def answer_question(query: str, history: list[dict] | None = None) -> CopilotAnswer:
    # Resolve the asset from the question, falling back to whatever was discussed
    # just before so follow-ups like "when was it last replaced?" still work.
    tag = resolve_equipment_in_query(query) or _tag_from_history(history)
    context = gather_graph_context(tag) if tag else None

    doc_ids = context.doc_ids if context else None
    chunks = vector_search(query, equipment_tag=tag, doc_ids=doc_ids)

    # Build the labelled context and the label -> citation lookup together, so the
    # labels the model cites map straight back to real sources.
    graph_block, label_map = _graph_block(context)
    passage_block, passage_map = _passage_block(chunks)
    label_map.update(passage_map)

    user_prompt = _user_prompt(query, graph_block, passage_block, history)
    raw, usage = complete_json_verbose(_SYSTEM, user_prompt)

    answer = (raw.get("answer") or "").strip()
    cited = [label for label in raw.get("citations", []) if label in label_map]
    citations = _order_citations(_dedupe_citations(label_map[label] for label in cited))

    return CopilotAnswer(
        answer=answer,
        citations=citations,
        resolved_equipment=tag,
        context_used={
            "graph_facts": graph_block or None,
            "passages": [
                {"label": f"D{i + 1}", "doc_id": c.doc_id, "source": c.source,
                 "score": round(c.score, 3) if c.score is not None else None, "snippet": _short(c.text)}
                for i, c in enumerate(chunks)
            ],
        },
        usage=usage,
    )


# --- prompt assembly ---

def _graph_block(ctx: GraphContext | None) -> tuple[str, dict[str, Citation]]:
    """Render graph facts with citable labels, and the matching citation objects."""
    if ctx is None:
        return "", {}

    labels: dict[str, Citation] = {}
    lines = [f"EQUIPMENT: {ctx.tag} ({ctx.name}), type {ctx.type}.", f"HEALTH: {ctx.health_line}"]

    if ctx.prediction:
        p = ctx.prediction
        lines.append(
            f"PREDICTION [PREDICTION]: {p.failure_label}, {p.risk_level} risk, {p.confidence}% confidence. "
            f"Next projected around {p.predicted_center}. Evidence: "
            f"{', '.join(e.wo_id for e in p.evidence)}."
        )
        labels["PREDICTION"] = Citation(
            type="prediction", ref=ctx.tag,
            title=f"{p.failure_label}: {p.risk_level} risk ({p.confidence}%)",
            snippet=p.explanation, equipment_tag=ctx.tag,
        )

    if ctx.timeline:
        lines.append("RECENT EVENTS:")
        for item in ctx.timeline:
            kind = "INCIDENT" if item.kind == "incident" else (item.extra.get("wo_type") or "Work order")
            lines.append(f"  [{item.id}] {item.date} ({kind}): {_short(item.description)}")
            labels[item.id] = Citation(
                type="incident" if item.kind == "incident" else "workorder",
                ref=item.id, title=f"{kind} {item.date}",
                snippet=_short(item.description), equipment_tag=ctx.tag,
            )

    if ctx.documents:
        # Make each linked document citable by its doc_id, so a question like
        # "which regulation covers hot work here?" can cite OISD-STD-105 straight
        # from the graph even if no passage from it was retrieved.
        lines.append("LINKED DOCUMENTS:")
        for d in ctx.documents:
            lines.append(f"  [{d.doc_id}] {d.title} ({d.label})")
            labels[d.doc_id] = Citation(
                type="document", ref=d.doc_id, title=d.title, snippet=d.label, equipment_tag=ctx.tag
            )

    return "\n".join(lines), labels


def _passage_block(chunks: list[ChunkHit]) -> tuple[str, dict[str, Citation]]:
    """Render retrieved document passages as [D1], [D2] ... with their sources."""
    if not chunks:
        return "", {}

    labels: dict[str, Citation] = {}
    lines = []
    for i, c in enumerate(chunks):
        label = f"D{i + 1}"
        lines.append(f"[{label}] (source: {c.source}): {_short(c.text, 500)}")
        labels[label] = Citation(
            type="document", ref=c.doc_id or c.source or label,
            title=c.source, snippet=_short(c.text, 240), score=c.score,
        )
    return "\n".join(lines), labels


def _user_prompt(query: str, graph_block: str, passage_block: str, history: list[dict] | None) -> str:
    parts = []
    if history:
        recent = "\n".join(f"{h.get('role')}: {h.get('content')}" for h in history[-4:])
        parts.append(f"EARLIER IN THIS CONVERSATION:\n{recent}")
    parts.append("GRAPH FACTS:\n" + (graph_block or "(none)"))
    parts.append("DOCUMENT PASSAGES:\n" + (passage_block or "(none)"))
    parts.append(f"QUESTION: {query}")
    return "\n\n".join(parts)


# --- small helpers ---

def _tag_from_history(history: list[dict] | None) -> str | None:
    """Carry forward the most recently discussed asset for follow-up questions."""
    if not history:
        return None
    for turn in reversed(history):
        tag = resolve_equipment_in_query(turn.get("content", ""))
        if tag:
            return tag
    return None


def _short(text: str | None, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _dedupe_citations(citations) -> list[Citation]:
    """Drop repeats that point at the same source (e.g. two chunks of one doc)."""
    seen: set[tuple[str, str]] = set()
    unique: list[Citation] = []
    for c in citations:
        key = (c.type, c.ref)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _order_citations(citations: list[Citation]) -> list[Citation]:
    """
    Order graph evidence before documents, and rank documents by their real
    retrieval score. No fabricated confidence: graph items simply keep their
    incoming (already meaningful) order within their type.
    """
    return sorted(
        citations,
        key=lambda c: (_TYPE_PRIORITY.get(c.type, 99), -(c.score or 0.0)),
    )
