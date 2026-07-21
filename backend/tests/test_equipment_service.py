"""
Equipment 360 query layer against the seeded graph (live Neo4j, no LLM cost).

Skips if the graph isn't seeded, so it never fails on an empty database.
"""

import pytest

from app.services.equipment_service import get_equipment_360


def _require_seed():
    if get_equipment_360("P-101") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def test_p101_biography_has_bearing_history_and_manual():
    _require_seed()
    r = get_equipment_360("P-101")

    assert r.summary.tag == "P-101"
    wo_ids = {t.id for t in r.timeline if t.kind == "workorder"}
    # The three bearing replacements that form the prediction evidence trail.
    assert {"WO-1001", "WO-1015", "WO-1041"} <= wo_ids

    manuals = {d.title for d in r.documents if d.relationship == "HAS_MANUAL"}
    assert "manual-pump-grundfos" in manuals


def test_t205_biography_has_incident_and_governing_regulation():
    _require_seed()
    r = get_equipment_360("T-205")

    assert any(t.kind == "incident" and t.id == "INC-2023-41" for t in r.timeline)
    governed = {d.doc_id for d in r.documents if d.relationship == "GOVERNED_BY"}
    assert "OISD-STD-105" in governed


def test_timeline_sorted_by_date_desc():
    _require_seed()
    dates = [t.date for t in get_equipment_360("P-101").timeline if t.date]
    assert dates == sorted(dates, reverse=True)


def test_unknown_tag_returns_none():
    assert get_equipment_360("ZZ-999") is None
