"""
Intervention engine against the seeded graph (deterministic; no LLM).
The near-miss recall on T-205 is the assertion that matters most.
"""

import pytest

from app.services.equipment_service import get_equipment_360
from app.services.intervention_service import evaluate_permit


def _require_seed():
    if get_equipment_360("T-205") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def test_t205_hot_work_recalls_near_miss_and_cites_oisd105():
    _require_seed()
    result = evaluate_permit("Hot Work", "T-205", "weld a new nozzle near the vent")

    # The 2023 near-miss must be recalled, as a critical item.
    assert any(
        i.severity == "critical" and i.citation and i.citation.type == "incident" and i.citation.ref == "INC-2023-41"
        for i in result.items
    ), "T-205 hot work must recall INC-2023-41"

    # And OISD-STD-105 (which governs T-205) must be cited.
    assert any(i.citation and i.citation.ref == "OISD-STD-105" for i in result.items)
    assert result.has_blocking


def test_p101_hot_work_does_not_fabricate_a_near_miss():
    _require_seed()
    result = evaluate_permit("Hot Work", "P-101", "weld a support bracket")

    # P-101 has no incident on record, so no incident item may appear.
    assert not any(i.citation and i.citation.type == "incident" for i in result.items)


def test_benign_permit_invents_nothing():
    _require_seed()
    result = evaluate_permit("General Maintenance", "HX-301", "routine gasket check")

    assert not result.has_blocking
    assert not any(i.severity == "critical" for i in result.items)
    assert not any(i.citation and i.citation.type == "incident" for i in result.items)
