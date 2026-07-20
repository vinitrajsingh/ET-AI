"""
Stage 4: MERGE entities and relationships into Neo4j.

This is where the "P-101 stays one node" promise is kept. Every node is written
with MERGE on its schema key, then enriched with `SET n += props`, so re-ingesting
a document attaches new facts to the existing node instead of duplicating it. We
only SET properties that are present, so a later, sparser document never blanks
out a value an earlier one filled in.

Returns simple counts (created vs merged) so the pipeline can report what changed.
"""

from app.db.neo4j_client import get_driver
from app.db.schema import Node, Rel, merge_key
from app.ingestion.entity_extraction import ExtractedEntities
from app.ingestion.relationship_extraction import Relationship


def merge_document_graph(
    doc_meta: dict,
    entities: ExtractedEntities,
    relationships: list[Relationship],
) -> dict:
    """Write the document node, its entities, and their edges in one session."""
    # Only keep people who are actually connected to something. Free-text
    # extraction (e.g. a regulation's committee list) yields names we don't want
    # as dangling nodes cluttering the graph.
    linked_people = {r.start_value for r in relationships if r.start == Node.PERSON}
    nodes = _collect_nodes(doc_meta, entities, linked_people)

    created = 0
    with get_driver().session() as session:
        for label, key_value, props in nodes:
            created += _merge_node(session, label, key_value, props)
        rels_written = sum(_merge_rel(session, r) for r in relationships)

    return {
        "nodes_total": len(nodes),
        "nodes_created": created,
        "nodes_merged": len(nodes) - created,
        "relationships_written": rels_written,
    }


def _collect_nodes(
    doc_meta: dict, e: ExtractedEntities, linked_people: set[str]
) -> list[tuple[Node, str, dict]]:
    """Flatten everything into (label, key_value, other_props) tuples to MERGE."""
    nodes: list[tuple[Node, str, dict]] = [
        (Node.DOCUMENT, doc_meta["doc_id"], _without_key(Node.DOCUMENT, doc_meta))
    ]

    for eq in e.equipment:
        nodes.append((Node.EQUIPMENT, eq.tag, {"name": eq.name, "type": eq.type, "location": eq.location}))
    for p in e.people:
        if p.name in linked_people:
            nodes.append((Node.PERSON, p.name, {"role": p.role}))
    for i in e.incidents:
        if i.id:
            nodes.append((Node.INCIDENT, i.id, {"date": i.date, "title": i.title, "description": i.description}))
    for w in e.work_orders:
        nodes.append((Node.WORK_ORDER, w.wo_id, {
            "date": w.date, "wo_type": w.wo_type, "description": w.description,
            "parts_used": w.parts_used, "cost": w.cost, "technician": w.technician,
            "status": w.status, "source_doc": doc_meta["doc_id"],
        }))
    for r in e.regulations:
        if r.code:
            nodes.append((Node.REGULATION, r.code, {"title": r.title, "clause": r.clause, "description": r.description}))
    for f in e.failure_modes:
        # A failure mode only means something attached to equipment; skip stray ones.
        if f.name and f.equipment_tag:
            nodes.append((Node.FAILURE_MODE, f.name, {"description": f.description}))

    return nodes


def _merge_node(session, label: Node, key_value: str, props: dict) -> int:
    """MERGE one node on its key, enrich with non-null props. Returns 1 if newly created."""
    key = merge_key(label)
    clean = {k: v for k, v in props.items() if v is not None}
    cypher = f"MERGE (n:{label.value} {{{key}: $key_value}}) SET n += $props"
    summary = session.run(cypher, key_value=key_value, props=clean).consume()
    return summary.counters.nodes_created


def _merge_rel(session, r: Relationship) -> int:
    """MATCH both endpoints by key and MERGE the edge. Returns 1 if the edge is new."""
    start_key = merge_key(r.start)
    end_key = merge_key(r.end)
    cypher = (
        f"MATCH (a:{r.start.value} {{{start_key}: $a}}) "
        f"MATCH (b:{r.end.value} {{{end_key}: $b}}) "
        f"MERGE (a)-[rel:{r.rel.value}]->(b)"
    )
    summary = session.run(cypher, a=r.start_value, b=r.end_value).consume()
    return summary.counters.relationships_created


def _without_key(label: Node, meta: dict) -> dict:
    """Document props minus its MERGE key (the key is set by the MERGE itself)."""
    key = merge_key(label)
    return {k: v for k, v in meta.items() if k != key}
