"""
Prediction engine over the seeded graph (live Neo4j, no LLM).

Deterministic because the reference date is pinned in config, so the interval
math and risk level are the same on every run.
"""

import pytest

from app.services.prediction_service import get_predictions


def _require_seed():
    if not get_predictions("P-101"):
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def test_p101_detects_the_three_bearing_failures():
    _require_seed()
    p = get_predictions("P-101")[0]

    assert p.status == "predicted"
    assert p.failure_type == "bearing"
    assert p.cycles == 3
    # Exactly the bearing trail, in date order. WO-1003 (a seal job that mentions
    # "no bearing work") must not sneak in.
    assert [e.wo_id for e in p.evidence] == ["WO-1001", "WO-1015", "WO-1041"]


def test_p101_mean_interval_and_risk():
    _require_seed()
    p = get_predictions("P-101")[0]

    assert 17.0 <= p.mean_interval_months <= 18.0
    # Current cycle sits right at the mean, so it must read as due, not calm.
    assert p.risk_level in {"Elevated", "High"}


def test_p101_has_confidence_and_explanation():
    _require_seed()
    p = get_predictions("P-101")[0]

    # Confidence is a plain 0-100 score derived from history + consistency, no ML.
    assert isinstance(p.confidence, int) and 0 <= p.confidence <= 100
    # The explanation must name the mechanism, not just the verdict.
    assert "average" in p.explanation.lower()
    assert p.risk_level in p.explanation


def test_p101_evidence_is_date_sorted():
    _require_seed()
    p = get_predictions("P-101")[0]
    dates = [e.date for e in p.evidence]
    assert dates == sorted(dates)


def test_asset_without_recurring_failures_makes_no_prediction():
    _require_seed()
    # HX-301 has tube/inspection work but no recurring bearing failures.
    predicted = [r for r in get_predictions("HX-301") if r.status == "predicted"]
    assert predicted == [], "No fabricated prediction should exist for HX-301"
