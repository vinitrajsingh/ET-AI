"""
Equipment 360 query layer: assembles a machine's whole life from the graph.

Pure Neo4j reads, no AI. Each function answers one section of the 360 view and
returns plain data; get_equipment_360 stitches them into one response. The health
snapshot is intentionally just raw counts, no prediction (that is Phase 4, and it
slots into the same structure later).
"""

from pydantic import BaseModel, Field

from app.db.neo4j_client import get_driver

# Relationship-type -> human label for the documents section. Kept here so the
# backend owns the vocabulary and the frontend just renders it.
_DOC_RELATION_LABELS = {
    "HAS_MANUAL": "Manual",
    "GOVERNED_BY": "Governing regulation",
    "MENTIONS": "Referenced in",
}


# --- Response models ---

class EquipmentSummary(BaseModel):
    tag: str
    name: str | None = None
    type: str | None = None
    location: str | None = None


class TimelineItem(BaseModel):
    kind: str  # "workorder" | "incident"
    id: str
    date: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    extra: dict = Field(default_factory=dict)


class DocumentLink(BaseModel):
    doc_id: str
    title: str | None = None
    type: str | None = None
    relationship: str  # raw rel type (HAS_MANUAL / GOVERNED_BY / MENTIONS)
    label: str  # friendly label for that relationship


class PersonWork(BaseModel):
    name: str
    role: str | None = None
    jobs: int = 0


class HealthSnapshot(BaseModel):
    total_work_orders: int = 0
    corrective_count: int = 0
    preventive_count: int = 0
    open_work_orders: int = 0
    last_work_order_date: str | None = None
    incident_count: int = 0


class Equipment360Response(BaseModel):
    summary: EquipmentSummary
    timeline: list[TimelineItem] = Field(default_factory=list)
    documents: list[DocumentLink] = Field(default_factory=list)
    people: list[PersonWork] = Field(default_factory=list)
    health: HealthSnapshot


class EquipmentListItem(BaseModel):
    tag: str
    name: str | None = None
    work_orders: int = 0
    incidents: int = 0


# --- Queries ---

def list_equipment() -> list[EquipmentListItem]:
    """Every equipment with its work-order and incident counts, for the grid."""
    cypher = """
        MATCH (e:Equipment)
        OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w:WorkOrder)
        OPTIONAL MATCH (e)-[:HAS_INCIDENT]->(i:Incident)
        RETURN e.tag AS tag, e.name AS name,
               count(DISTINCT w) AS work_orders, count(DISTINCT i) AS incidents
        ORDER BY e.tag
    """
    with get_driver().session() as session:
        return [EquipmentListItem(**r.data()) for r in session.run(cypher)]


def get_equipment_summary(tag: str) -> EquipmentSummary | None:
    """The equipment node's own properties. None if the tag does not exist."""
    cypher = "MATCH (e:Equipment {tag: $tag}) RETURN e.tag AS tag, e.name AS name, e.type AS type, e.location AS location"
    with get_driver().session() as session:
        record = session.run(cypher, tag=tag).single()
        return EquipmentSummary(**record.data()) if record else None


def get_equipment_timeline(tag: str) -> list[TimelineItem]:
    """
    Work orders and incidents merged into one list, newest first.

    We fetch the two kinds separately (clearer than a UNION with padded columns)
    and merge in Python. Open/In-Progress work orders have no completion date, so
    they carry their reported date and naturally sort to the top with the newest.
    """
    wo_cypher = """
        MATCH (e:Equipment {tag: $tag})-[:HAS_WORKORDER]->(w:WorkOrder)
        RETURN w.wo_id AS id, w.date AS date, w.wo_type AS wo_type,
               w.description AS description, w.status AS status,
               w.cost AS cost, w.parts_used AS parts_used, w.technician AS technician
    """
    inc_cypher = """
        MATCH (e:Equipment {tag: $tag})-[:HAS_INCIDENT]->(i:Incident)
        RETURN i.id AS id, i.date AS date, i.title AS title, i.description AS description
    """
    items: list[TimelineItem] = []
    with get_driver().session() as session:
        for w in session.run(wo_cypher, tag=tag):
            items.append(TimelineItem(
                kind="workorder", id=w["id"], date=w["date"],
                title=w["wo_type"], description=w["description"], status=w["status"],
                extra={"wo_type": w["wo_type"], "cost": w["cost"],
                       "parts_used": w["parts_used"], "technician": w["technician"]},
            ))
        for i in session.run(inc_cypher, tag=tag):
            items.append(TimelineItem(
                kind="incident", id=i["id"], date=i["date"],
                title=i["title"] or "Incident / near-miss", description=i["description"],
            ))

    # Sort by date descending; items without a date fall to the bottom.
    items.sort(key=lambda it: it.date or "", reverse=True)
    return items


def get_equipment_documents(tag: str) -> list[DocumentLink]:
    """Documents attached to the equipment, each tagged with its relationship."""
    # Curated edges point equipment -> document; MENTIONS points document -> equipment.
    cypher = """
        MATCH (e:Equipment {tag: $tag})-[r:HAS_MANUAL|GOVERNED_BY]->(d:Document)
        RETURN d.doc_id AS doc_id, d.title AS title, d.type AS type, type(r) AS relationship
        UNION
        MATCH (e:Equipment {tag: $tag})<-[r:MENTIONS]-(d:Document)
        RETURN d.doc_id AS doc_id, d.title AS title, d.type AS type, type(r) AS relationship
    """
    with get_driver().session() as session:
        return [
            DocumentLink(**r.data(), label=_DOC_RELATION_LABELS.get(r["relationship"], r["relationship"]))
            for r in session.run(cypher, tag=tag)
        ]


def get_equipment_people(tag: str) -> list[PersonWork]:
    """People who worked on the equipment, with how many work orders each did."""
    # Person nodes carry no role in this corpus yet, so we don't select it (that
    # keeps Neo4j from warning about a missing property); PersonWork.role stays
    # optional for when roles are added.
    cypher = """
        MATCH (e:Equipment {tag: $tag})<-[:WORKED_ON]-(p:Person)
        OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w:WorkOrder) WHERE w.technician = p.name
        RETURN p.name AS name, count(w) AS jobs
        ORDER BY jobs DESC, name
    """
    with get_driver().session() as session:
        return [PersonWork(**r.data()) for r in session.run(cypher, tag=tag)]


def get_equipment_health_snapshot(tag: str) -> HealthSnapshot:
    """Raw maintenance facts for the header stat chips. No prediction here."""
    cypher = """
        MATCH (e:Equipment {tag: $tag})
        OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w:WorkOrder)
        OPTIONAL MATCH (e)-[:HAS_INCIDENT]->(i:Incident)
        RETURN
          count(DISTINCT w) AS total_work_orders,
          count(DISTINCT CASE WHEN w.wo_type = 'Corrective' THEN w END) AS corrective_count,
          count(DISTINCT CASE WHEN w.wo_type = 'Preventive' THEN w END) AS preventive_count,
          count(DISTINCT CASE WHEN w.status <> 'Closed' THEN w END) AS open_work_orders,
          max(w.date) AS last_work_order_date,
          count(DISTINCT i) AS incident_count
    """
    with get_driver().session() as session:
        record = session.run(cypher, tag=tag).single()
        return HealthSnapshot(**record.data())


def get_equipment_360(tag: str) -> Equipment360Response | None:
    """Full 360 payload for one equipment. None when the tag is unknown (router -> 404)."""
    summary = get_equipment_summary(tag)
    if summary is None:
        return None

    return Equipment360Response(
        summary=summary,
        timeline=get_equipment_timeline(tag),
        documents=get_equipment_documents(tag),
        people=get_equipment_people(tag),
        health=get_equipment_health_snapshot(tag),
    )
