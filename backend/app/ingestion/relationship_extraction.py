"""
Stage 3: entities -> relationships.

Turns the flat entity lists into graph edges using the schema's relationship
types. The rules are deliberately simple and derived from what the entities
already state, so the graph shape stays predictable:

  Document   MENTIONS         Equipment   (any equipment the doc refers to)
  Equipment  HAS_WORKORDER    WorkOrder
  Person     WORKED_ON        Equipment   (the technician on a work order)
  Equipment  HAS_INCIDENT     Incident
  Regulation GOVERNS          Equipment
  Equipment  HAS_FAILURE_MODE FailureMode
"""

from pydantic import BaseModel

from app.db.schema import Node, Rel
from app.ingestion.entity_extraction import ExtractedEntities

_NOT_A_PERSON = {"unassigned", "auto-pm scheduler"}


class Relationship(BaseModel):
    """One edge, described by node types and their MERGE-key values."""

    start: Node
    start_value: str
    rel: Rel
    end: Node
    end_value: str


def build_relationships(entities: ExtractedEntities, doc_id: str) -> list[Relationship]:
    rels: list[Relationship] = []

    for e in entities.equipment:
        rels.append(_edge(Node.DOCUMENT, doc_id, Rel.MENTIONS, Node.EQUIPMENT, e.tag))

    for w in entities.work_orders:
        rels.append(_edge(Node.EQUIPMENT, w.equipment_tag, Rel.HAS_WORKORDER, Node.WORK_ORDER, w.wo_id))
        if w.technician and w.technician.lower() not in _NOT_A_PERSON:
            rels.append(_edge(Node.PERSON, w.technician, Rel.WORKED_ON, Node.EQUIPMENT, w.equipment_tag))

    for i in entities.incidents:
        if i.id and i.equipment_tag:
            rels.append(_edge(Node.EQUIPMENT, i.equipment_tag, Rel.HAS_INCIDENT, Node.INCIDENT, i.id))

    for r in entities.regulations:
        if r.code and r.equipment_tag:
            rels.append(_edge(Node.REGULATION, r.code, Rel.GOVERNS, Node.EQUIPMENT, r.equipment_tag))

    for f in entities.failure_modes:
        if f.name and f.equipment_tag:
            rels.append(_edge(Node.EQUIPMENT, f.equipment_tag, Rel.HAS_FAILURE_MODE, Node.FAILURE_MODE, f.name))

    return _dedupe(rels)


def _edge(start: Node, start_value: str, rel: Rel, end: Node, end_value: str) -> Relationship:
    return Relationship(start=start, start_value=start_value, rel=rel, end=end, end_value=end_value)


def _dedupe(rels: list[Relationship]) -> list[Relationship]:
    seen: set[tuple] = set()
    unique: list[Relationship] = []
    for r in rels:
        key = (r.start, r.start_value, r.rel, r.end, r.end_value)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique
