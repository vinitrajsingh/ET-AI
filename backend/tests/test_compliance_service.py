"""
Compliance engine against the seeded graph (deterministic; no LLM).
Findings are stable because the interval math uses the fixed reference date.
"""

import pytest

from app.services.compliance_service import (
    evaluate_equipment_compliance,
    evaluate_fleet_compliance,
)
from app.services.equipment_service import get_equipment_360


def _require_seed():
    if get_equipment_360("B-7") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def _find(findings, rule_code):
    return next((f for f in findings if f.rule_code == rule_code), None)


def test_b7_boiler_inspection_reads_real_work_orders():
    _require_seed()
    boiler = _find(evaluate_equipment_compliance("B-7"), "STAT-BOILER-INSP")

    assert boiler is not None
    # Computed from the real annual-inspection work orders, latest is WO-1072.
    assert boiler.status == "compliant"
    assert boiler.evidence_ref == "WO-1072"
    assert boiler.category == "Safety"


def test_no_false_gap_when_evidence_satisfies_the_rule():
    _require_seed()
    boiler = _find(evaluate_equipment_compliance("B-7"), "STAT-BOILER-INSP")
    # A satisfied rule must not read as overdue or missing.
    assert boiler.status not in ("overdue", "missing_evidence")
    assert boiler.evidence_ref and boiler.evidence_date


def test_t205_has_safety_findings_for_hotwork_and_tank():
    _require_seed()
    findings = evaluate_equipment_compliance("T-205")

    hotwork = _find(findings, "OISD105-HOTWORK")
    assert hotwork is not None and hotwork.category == "Safety"
    assert hotwork.regulation_doc_id == "OISD-STD-105"
    assert hotwork.evidence_ref == "INC-2023-41"  # tied to the real near-miss

    tank = _find(findings, "TANK-THICKNESS")
    assert tank is not None and tank.evidence_ref == "WO-1012"


def test_fleet_covers_environment_and_full_hse_breakdown():
    _require_seed()
    fleet = evaluate_fleet_compliance()

    assert any(f.category == "Environment" for f in fleet.findings), "an environmental finding must exist"
    for category in ("Health", "Safety", "Environment"):
        assert fleet.category_breakdown[category]["total"] >= 1
