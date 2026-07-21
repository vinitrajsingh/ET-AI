"""
Guru Mode endpoints.

  POST /guru/notes                accept an audio file OR a typed transcript,
                                  transcribe (if audio), structure, and store
  GET  /guru/notes                list (optional equipment filter, held notes)
  POST /guru/notes/{id}/approve   promote a held note to trusted knowledge

The text-transcript path is deliberate demo insurance: live audio on stage is the
most likely thing to fail, so the same endpoint accepts a pre-typed transcript.
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import guru_service
from app.services.guru_service import GuruNoteOut

router = APIRouter(prefix="/guru", tags=["guru"])


@router.post("/notes", response_model=GuruNoteOut)
async def create_note(
    equipment_tag: str = Form(...),
    engineer_name: str = Form(...),
    transcript: str | None = Form(None),
    approved: bool = Form(True),  # senior engineers auto-approve; toggle off to hold for review
    audio: UploadFile | None = File(None),
) -> GuruNoteOut:
    language = "en"
    text = (transcript or "").strip()

    if audio is not None and audio.filename:
        text, language = _transcribe_upload(audio)

    if not text:
        raise HTTPException(status_code=400, detail="Provide an audio file or a transcript.")

    return guru_service.create_guru_note(equipment_tag, engineer_name, text, language=language, approved=approved)


@router.get("/notes", response_model=list[GuruNoteOut])
def list_notes(equipment_tag: str | None = None, include_unapproved: bool = False) -> list[GuruNoteOut]:
    return guru_service.list_guru_notes(equipment_tag, include_unapproved)


@router.post("/notes/{note_id}/approve")
def approve(note_id: str) -> dict:
    if not guru_service.approve_note(note_id):
        raise HTTPException(status_code=404, detail=f"Unknown note: {note_id}")
    return {"note_id": note_id, "approved": True}


def _transcribe_upload(audio: UploadFile) -> tuple[str, str]:
    """Save the upload to a temp file and run Whisper; 422 if audio can't be read."""
    from app.services.whisper_service import transcribe  # local import: Whisper is heavy

    suffix = Path(audio.filename or "note.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        result = transcribe(str(tmp_path))
        return result.text, result.language
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)
