"""
Permit lifecycle: create / read / list, plus a mirror node in the graph.

Postgres owns the permit record (status, acknowledgments, audit trail). We also
MERGE a small Permit node into Neo4j linked APPLIES_TO the equipment, so the
graph can answer relationship questions like "what active permits touch T-205?"
which the intervention engine uses for conflict detection.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.db.neo4j_client import get_driver
from app.db.postgres import Base, SessionLocal, engine
from app.models.permit import Permit


class PermitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permit_id: str
    permit_type: str
    equipment_tag: str
    description: str | None = None
    status: str
    created_by: str | None = None
    created_date: datetime
    acknowledged_items: list = []


def init_permit_storage() -> None:
    """Create the permits table if it does not exist. Safe to call on startup."""
    Base.metadata.create_all(engine, tables=[Permit.__table__])


def create_permit(
    permit_type: str,
    equipment_tag: str,
    description: str | None,
    created_by: str | None,
    acknowledged_items: list,
    status: str = "active",
) -> PermitOut:
    permit = Permit(
        permit_id="PMT-" + uuid.uuid4().hex[:6].upper(),
        permit_type=permit_type,
        equipment_tag=equipment_tag,
        description=description,
        status=status,
        created_by=created_by,
        created_date=datetime.utcnow(),
        acknowledged_items=acknowledged_items,
    )
    with SessionLocal() as db:
        db.add(permit)
        db.commit()
        db.refresh(permit)
        out = PermitOut.model_validate(permit)

    _merge_permit_node(out)
    return out


def get_permit(permit_id: str) -> PermitOut | None:
    with SessionLocal() as db:
        permit = db.get(Permit, permit_id)
        return PermitOut.model_validate(permit) if permit else None


def list_permits() -> list[PermitOut]:
    with SessionLocal() as db:
        rows = db.execute(select(Permit).order_by(Permit.created_date.desc())).scalars().all()
        return [PermitOut.model_validate(p) for p in rows]


def active_permits_for(equipment_tag: str, exclude_permit_id: str | None = None) -> list[PermitOut]:
    """Active permits already on this asset, for the conflicting-operations check."""
    with SessionLocal() as db:
        stmt = select(Permit).where(Permit.equipment_tag == equipment_tag, Permit.status == "active")
        rows = db.execute(stmt).scalars().all()
        return [PermitOut.model_validate(p) for p in rows if p.permit_id != exclude_permit_id]


def _merge_permit_node(permit: PermitOut) -> None:
    """Mirror the permit into the graph as (Permit)-[:APPLIES_TO]->(Equipment)."""
    cypher = """
        MERGE (p:Permit {permit_id: $permit_id})
        SET p.permit_type = $permit_type, p.status = $status, p.created_date = $created_date
        WITH p
        MATCH (e:Equipment {tag: $tag})
        MERGE (p)-[:APPLIES_TO]->(e)
    """
    with get_driver().session() as session:
        session.run(
            cypher,
            permit_id=permit.permit_id, permit_type=permit.permit_type, status=permit.status,
            created_date=permit.created_date.isoformat(), tag=permit.equipment_tag,
        )
