"""
Graph schema: the single source of truth for how SANJEEVANI's knowledge graph
is shaped in Neo4j.

Everything that writes to the graph (graph_merge, later features) imports the
node labels, relationship types, and MERGE keys from here so we never drift.
The golden rule of this project lives in MERGE_KEYS: each node type merges on a
stable business key (Equipment on its tag, WorkOrder on its id, ...), so
re-ingesting the same document attaches new facts to the existing node instead
of creating a duplicate.
"""

from enum import Enum


class Node(str, Enum):
    """Node labels used in the graph."""

    EQUIPMENT = "Equipment"
    DOCUMENT = "Document"
    INCIDENT = "Incident"
    WORK_ORDER = "WorkOrder"
    PERMIT = "Permit"
    REGULATION = "Regulation"
    PERSON = "Person"
    GURU_NOTE = "GuruNote"
    FAILURE_MODE = "FailureMode"


class Rel(str, Enum):
    """Relationship types. Direction is documented in RELATIONSHIPS below."""

    HAS_WORKORDER = "HAS_WORKORDER"
    HAS_INCIDENT = "HAS_INCIDENT"
    APPLIES_TO = "APPLIES_TO"
    GOVERNS = "GOVERNS"
    ABOUT = "ABOUT"
    MENTIONS = "MENTIONS"
    WORKED_ON = "WORKED_ON"
    HAS_FAILURE_MODE = "HAS_FAILURE_MODE"


# (start_label, REL, end_label). Kept as data so we can document and, if needed,
# validate the graph shape in one place.
RELATIONSHIPS: list[tuple[Node, Rel, Node]] = [
    (Node.EQUIPMENT, Rel.HAS_WORKORDER, Node.WORK_ORDER),
    (Node.EQUIPMENT, Rel.HAS_INCIDENT, Node.INCIDENT),
    (Node.PERMIT, Rel.APPLIES_TO, Node.EQUIPMENT),
    (Node.REGULATION, Rel.GOVERNS, Node.EQUIPMENT),
    (Node.GURU_NOTE, Rel.ABOUT, Node.EQUIPMENT),
    (Node.DOCUMENT, Rel.MENTIONS, Node.EQUIPMENT),
    (Node.PERSON, Rel.WORKED_ON, Node.EQUIPMENT),
    (Node.EQUIPMENT, Rel.HAS_FAILURE_MODE, Node.FAILURE_MODE),
]


# The property each node MERGEs on. This is the anti-duplication contract: any
# writer must MERGE on exactly this key, then SET the rest of the properties.
MERGE_KEYS: dict[Node, str] = {
    Node.EQUIPMENT: "tag",
    Node.DOCUMENT: "doc_id",
    Node.INCIDENT: "id",
    Node.WORK_ORDER: "wo_id",
    Node.PERMIT: "permit_id",
    Node.REGULATION: "code",
    Node.PERSON: "name",
    Node.GURU_NOTE: "note_id",
    Node.FAILURE_MODE: "name",
}


# The full property set we expect per node type. Not enforced by Neo4j (which is
# schema-free), but documented here so extraction and merge stay consistent.
# The MERGE key is always the first item.
NODE_PROPERTIES: dict[Node, list[str]] = {
    Node.EQUIPMENT: ["tag", "name", "type", "location"],
    Node.DOCUMENT: ["doc_id", "title", "type", "version", "upload_date", "source"],
    Node.INCIDENT: ["id", "date", "title", "description"],
    Node.WORK_ORDER: [
        "wo_id", "date", "wo_type", "description", "parts_used",
        "cost", "technician", "status", "source_doc",
    ],
    Node.PERMIT: ["permit_id", "permit_type", "equipment_tag", "status", "created_date"],
    Node.REGULATION: ["code", "title", "clause", "description"],
    Node.PERSON: ["name", "role"],
    Node.GURU_NOTE: ["note_id", "symptom", "meaning", "source", "approved"],
    Node.FAILURE_MODE: ["name", "description"],
}


def merge_key(node: Node) -> str:
    """Return the unique property a node type merges on."""
    return MERGE_KEYS[node]


# Uniqueness constraints. In Neo4j a uniqueness constraint also creates the
# backing index, so MERGE stays fast and duplicate keys are rejected outright.
def _constraint_statements() -> list[str]:
    stmts = []
    for node, key in MERGE_KEYS.items():
        name = f"uniq_{node.value.lower()}_{key}"
        stmts.append(
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{node.value}) REQUIRE n.{key} IS UNIQUE"
        )
    return stmts


def setup_constraints() -> None:
    """
    Create every uniqueness constraint once. Idempotent thanks to IF NOT EXISTS,
    so it is safe to call on each app startup. Import here (not at module top) to
    avoid a circular import with the driver singleton.
    """
    from app.db.neo4j_client import get_driver

    with get_driver().session() as session:
        for stmt in _constraint_statements():
            session.run(stmt)
