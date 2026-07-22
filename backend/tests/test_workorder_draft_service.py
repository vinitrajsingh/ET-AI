"""
Work-order drafts from predictions (live Neo4j + Postgres). Cleans up the draft
and any approved work order so the demo timeline stays as designed.
"""

import pytest

from app.db.neo4j_client import get_driver
from app.db.postgres import SessionLocal
from app.models.workorder_draft import WorkOrderDraft
from app.services.equipment_service import get_equipment_360
from app.services.workorder_draft_service import approve_draft, draft_from_prediction


def _require_seed():
    if get_equipment_360("P-101") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def _cleanup(draft_id: str, wo_id: str | None = None) -> None:
    with SessionLocal() as db:
        draft = db.get(WorkOrderDraft, draft_id)
        if draft:
            db.delete(draft)
            db.commit()
    if wo_id:
        with get_driver().session() as session:
            session.run("MATCH (w:WorkOrder {wo_id: $id}) DETACH DELETE w", id=wo_id)


def test_draft_is_prefilled_from_the_bearing_prediction():
    _require_seed()
    draft = draft_from_prediction("P-101", "bearing")
    try:
        assert draft is not None
        assert draft.equipment_tag == "P-101"
        assert "bearing" in draft.task.lower()
        assert draft.priority in ("High", "Critical")  # from the Elevated risk
        assert draft.target_date  # from the predicted window
        # The three bearing work orders back the draft as justification.
        assert {"WO-1001", "WO-1015", "WO-1041"}.issubset(set(draft.justification["evidence_work_orders"]))
    finally:
        _cleanup(draft.draft_id if draft else "")


def test_approving_a_draft_creates_a_work_order_on_the_timeline():
    _require_seed()
    draft = draft_from_prediction("P-101", "bearing")
    approved = approve_draft(draft.draft_id)
    wo_id = approved.approved_wo_id
    try:
        assert approved.status == "approved" and wo_id
        assert wo_id in [t.id for t in get_equipment_360("P-101").timeline]
    finally:
        _cleanup(draft.draft_id, wo_id)


def test_no_prediction_returns_none_not_a_fabricated_draft():
    _require_seed()
    # HX-301 has no recurring bearing failure, so there is nothing to draft.
    assert draft_from_prediction("HX-301", "bearing") is None
