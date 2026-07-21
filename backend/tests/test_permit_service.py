"""
Permit creation and acknowledgment enforcement (live Neo4j + Postgres).

Cleans up any permit it creates so the demo's T-205 stays free of stray active
permits (which would otherwise show up as conflict interventions).
"""

import pytest
from fastapi.testclient import TestClient

import app.main as m
from app.db.neo4j_client import get_driver
from app.db.postgres import SessionLocal
from app.models.permit import Permit
from app.services.equipment_service import get_equipment_360

client = TestClient(m.app)


def _require_seed():
    if get_equipment_360("T-205") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def _delete_permit(permit_id: str) -> None:
    with SessionLocal() as db:
        permit = db.get(Permit, permit_id)
        if permit:
            db.delete(permit)
            db.commit()
    with get_driver().session() as session:
        session.run("MATCH (p:Permit {permit_id: $id}) DETACH DELETE p", id=permit_id)


def test_unacknowledged_critical_permit_is_rejected():
    _require_seed()
    res = client.post(
        "/permits",
        json={"permit_type": "Hot Work", "equipment_tag": "T-205", "description": "weld", "acknowledged": []},
    )
    assert res.status_code == 400


def test_acknowledged_permit_is_created_and_logged():
    _require_seed()
    evaluation = client.post(
        "/permits/evaluate",
        json={"permit_type": "Hot Work", "equipment_tag": "T-205", "description": "weld"},
    ).json()
    critical_ids = [i["id"] for i in evaluation["items"] if i["severity"] == "critical"]

    res = client.post(
        "/permits",
        json={
            "permit_type": "Hot Work", "equipment_tag": "T-205", "description": "weld",
            "created_by": "Test Officer", "acknowledged": critical_ids,
        },
    )
    assert res.status_code == 200
    permit_id = res.json()["permit_id"]
    try:
        assert len(res.json()["acknowledged_items"]) == len(critical_ids)
        detail = client.get(f"/permits/{permit_id}")
        assert detail.status_code == 200
        assert len(detail.json()["acknowledged_items"]) == len(critical_ids)
    finally:
        _delete_permit(permit_id)
