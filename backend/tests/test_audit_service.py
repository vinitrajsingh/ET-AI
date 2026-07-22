"""
Audit package assembly + PDF (live services). Creates a permit with
acknowledgments so the audit trail has content, then cleans it up.
"""

import pytest
from fastapi.testclient import TestClient

import app.main as m
from app.db.neo4j_client import get_driver
from app.db.postgres import SessionLocal
from app.models.permit import Permit
from app.services.audit_service import build_audit_package
from app.services.equipment_service import get_equipment_360
from app.services.pdf_service import render_audit_pdf

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


def test_audit_package_carries_evidence_incident_and_ack_logs():
    _require_seed()
    ev = client.post("/permits/evaluate", json={"permit_type": "Hot Work", "equipment_tag": "T-205", "description": "weld"}).json()
    critical = [i["id"] for i in ev["items"] if i["severity"] == "critical"]
    permit = client.post("/permits", json={
        "permit_type": "Hot Work", "equipment_tag": "T-205", "description": "weld",
        "created_by": "Test Officer", "acknowledged": critical,
    }).json()

    try:
        package = build_audit_package("fleet")

        # A compliance finding must carry its cited evidence.
        assert any(f.evidence_ref for f in package.compliance)
        # The T-205 near-miss must be in the incident history.
        assert any(i.id == "INC-2023-41" for i in package.incidents)
        # The acknowledgment log (the centerpiece) must be present and traceable.
        acknowledged = [a for p in package.permits for a in p.acknowledged]
        assert any(a.cited == "INC-2023-41" for a in acknowledged)

        pdf = render_audit_pdf(package)
        assert pdf[:5] == b"%PDF-" and len(pdf) > 1000
    finally:
        _delete_permit(permit["permit_id"])
