"""
Guru Mode: capture a retiring engineer's know-how as first-class graph knowledge.

A voice or typed note becomes a structured GuruNote (symptom, meaning, action),
stored ABOUT the equipment and RECORDED_BY the engineer, and credited to them by
name forever. Two rules matter: we structure only what the engineer actually said
(no invented symptoms), and unapproved notes stay held until an admin approves,
so tribal knowledge is trusted before it answers live questions.
"""

import logging
import uuid

from pydantic import BaseModel, Field

from app.db.neo4j_client import get_driver
from app.services.llm import complete_json

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You structure a plant engineer's spoken note about a piece of equipment. "
    "Extract only what the note actually says. Do not invent symptoms, causes, or "
    "actions. If a field is not stated, leave it an empty string."
)

_SCHEMA_HINT = """Return JSON with these keys:
{
  "symptom": "what the engineer observes (a sound, reading, behaviour)",
  "meaning": "what it indicates",
  "recommended_action": "what to do about it",
  "summary": "one short sentence capturing the whole note"
}"""


class StructuredNote(BaseModel):
    symptom: str = ""
    meaning: str = ""
    recommended_action: str = ""
    summary: str = ""


class GuruNoteOut(BaseModel):
    note_id: str
    equipment_tag: str
    engineer_name: str
    symptom: str = ""
    meaning: str = ""
    recommended_action: str = ""
    summary: str = ""
    transcript: str = ""
    language: str = "en"
    approved: bool = False


def structure_note(transcript: str, equipment_tag: str, engineer_name: str) -> StructuredNote:
    """One grounded LLM call turning a raw transcript into symptom/meaning/action."""
    if not transcript.strip():
        return StructuredNote()

    user = f"{_SCHEMA_HINT}\n\nEQUIPMENT: {equipment_tag}\nENGINEER: {engineer_name}\nNOTE:\n{transcript}"
    try:
        raw = complete_json(_SYSTEM, user)
        return StructuredNote(
            symptom=(raw.get("symptom") or "").strip(),
            meaning=(raw.get("meaning") or "").strip(),
            recommended_action=(raw.get("recommended_action") or "").strip(),
            summary=(raw.get("summary") or "").strip(),
        )
    except Exception as exc:
        # Structuring is best-effort. If it fails, keep the transcript so nothing
        # the engineer said is lost; just store it with empty structure.
        logger.warning("Guru note structuring failed, storing transcript only: %s", exc)
        return StructuredNote(summary=transcript[:200])


def create_guru_note(
    equipment_tag: str,
    engineer_name: str,
    transcript: str,
    language: str = "en",
    approved: bool = False,
    note_id: str | None = None,
) -> GuruNoteOut:
    """Structure and persist the note, linking it to the equipment and engineer."""
    structured = structure_note(transcript, equipment_tag, engineer_name)
    note_id = note_id or "GN-" + uuid.uuid4().hex[:6].upper()

    note = GuruNoteOut(
        note_id=note_id, equipment_tag=equipment_tag, engineer_name=engineer_name,
        symptom=structured.symptom, meaning=structured.meaning,
        recommended_action=structured.recommended_action, summary=structured.summary,
        transcript=transcript, language=language, approved=approved,
    )

    cypher = """
        MERGE (g:GuruNote {note_id: $note_id})
        SET g.symptom = $symptom, g.meaning = $meaning, g.recommended_action = $action,
            g.summary = $summary, g.transcript = $transcript, g.source = $engineer,
            g.language = $language, g.approved = $approved
        WITH g
        MATCH (e:Equipment {tag: $tag})
        MERGE (g)-[:ABOUT]->(e)
        MERGE (p:Person {name: $engineer})
        MERGE (g)-[:RECORDED_BY]->(p)
    """
    with get_driver().session() as session:
        session.run(
            cypher,
            note_id=note_id, symptom=note.symptom, meaning=note.meaning, action=note.recommended_action,
            summary=note.summary, transcript=transcript, engineer=engineer_name,
            language=language, approved=approved, tag=equipment_tag,
        )
    return note


def list_guru_notes(equipment_tag: str | None = None, include_unapproved: bool = False) -> list[GuruNoteOut]:
    """List guru notes, approved-only by default. Optionally filter by equipment."""
    where = []
    if equipment_tag:
        where.append("(g)-[:ABOUT]->(:Equipment {tag: $tag})")
    if not include_unapproved:
        where.append("g.approved = true")
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    cypher = f"""
        MATCH (g:GuruNote)
        {clause}
        OPTIONAL MATCH (g)-[:ABOUT]->(e:Equipment)
        RETURN g.note_id AS note_id, e.tag AS equipment_tag, g.source AS engineer_name,
               g.symptom AS symptom, g.meaning AS meaning, g.recommended_action AS recommended_action,
               g.summary AS summary, g.transcript AS transcript, g.language AS language, g.approved AS approved
        ORDER BY note_id
    """
    with get_driver().session() as session:
        return [GuruNoteOut(**_clean(r.data())) for r in session.run(cypher, tag=equipment_tag)]


def approve_note(note_id: str) -> bool:
    """Mark a held note as approved. Returns True if the note exists."""
    cypher = "MATCH (g:GuruNote {note_id: $note_id}) SET g.approved = true RETURN g.note_id AS id"
    with get_driver().session() as session:
        return session.run(cypher, note_id=note_id).single() is not None


def _clean(row: dict) -> dict:
    """Neo4j returns None for missing string props; coerce to the model's defaults."""
    row["equipment_tag"] = row.get("equipment_tag") or ""
    for key in ("symptom", "meaning", "recommended_action", "summary", "transcript"):
        row[key] = row.get(key) or ""
    row["language"] = row.get("language") or "en"
    row["approved"] = bool(row.get("approved"))
    return row
