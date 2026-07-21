"""
Copilot smoke tests. These DO call the LLM, so they are kept few and focused.
Skips if the corpus isn't seeded.
"""

import pytest

from app.services.copilot_service import answer_question
from app.services.retrieval_service import gather_graph_context


def _require_seed():
    if gather_graph_context("P-101") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def test_structured_question_grounds_in_work_orders():
    _require_seed()
    a = answer_question("When was P-101's bearing last replaced?")

    assert a.resolved_equipment == "P-101"
    # The last bearing work order is in the grounding context, and the answer cites
    # something (not an ungrounded guess).
    assert "WO-1041" in (a.context_used.get("graph_facts") or "")
    assert len(a.citations) >= 1


def test_off_corpus_question_is_declined_without_citations():
    _require_seed()
    a = answer_question("What is the airspeed of an unladen swallow?")

    # An honest copilot admits ignorance and fabricates no sources.
    assert a.citations == []
    assert "enough information" in a.answer.lower()
