"""
Guru Mode: capture, approval gate, and the copilot resurrection.

Uses the LLM for structuring + one copilot answer, so kept minimal. Each test
cleans up the note it creates so the seeded flagship note is the only one left.
"""

import pytest

from app.db.neo4j_client import get_driver
from app.services.copilot_service import answer_question
from app.services.equipment_service import get_equipment_360
from app.services.guru_service import approve_note, create_guru_note, list_guru_notes

_TRANSCRIPT = (
    "On pump P-101, when the bearing makes a faint whistling sound it usually fails "
    "within about two weeks, and the pressure gauge shows nothing beforehand."
)


def _require_seed():
    if get_equipment_360("P-101") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def _delete_note(note_id: str) -> None:
    with get_driver().session() as session:
        session.run("MATCH (g:GuruNote {note_id: $id}) DETACH DELETE g", id=note_id)


def test_create_note_links_to_equipment_and_engineer():
    _require_seed()
    note = create_guru_note("P-101", "Test Guru", _TRANSCRIPT, approved=True)
    try:
        assert note.symptom, "symptom should be extracted"
        # Linked ABOUT the equipment and RECORDED_BY the engineer.
        with get_driver().session() as s:
            row = s.run(
                "MATCH (g:GuruNote {note_id:$id})-[:ABOUT]->(:Equipment {tag:'P-101'}) "
                "MATCH (g)-[:RECORDED_BY]->(p:Person {name:'Test Guru'}) RETURN g.note_id AS id",
                id=note.note_id,
            ).single()
        assert row is not None
    finally:
        _delete_note(note.note_id)


def test_approval_gate_hides_then_reveals():
    _require_seed()
    note = create_guru_note("P-101", "Held Guru", _TRANSCRIPT, approved=False)
    try:
        approved_ids = {n.note_id for n in list_guru_notes("P-101")}
        assert note.note_id not in approved_ids, "unapproved note must be hidden"

        all_ids = {n.note_id for n in list_guru_notes("P-101", include_unapproved=True)}
        assert note.note_id in all_ids

        approve_note(note.note_id)
        assert note.note_id in {n.note_id for n in list_guru_notes("P-101")}
    finally:
        _delete_note(note.note_id)


def test_copilot_credits_the_engineer_by_name():
    _require_seed()
    # Ensure the flagship note exists (idempotent via a fixed id); do NOT delete it,
    # it is the demo seed.
    create_guru_note("P-101", "Rajesh Kumar", _TRANSCRIPT, approved=True, note_id="GN-RAJESH-P101")

    answer = answer_question("What does the whistling sound on P-101 mean?")
    guru_citations = [c for c in answer.citations if c.type == "guru"]

    # The guru note is grounding the answer and is cited by the engineer's name.
    # (The exact prose wording is the LLM's; what we guarantee is the attribution.)
    assert guru_citations, "the guru note must be cited"
    assert any((c.title or "").strip() for c in guru_citations), "citation must credit an engineer by name"
