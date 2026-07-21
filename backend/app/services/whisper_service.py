"""
Local voice transcription for Guru Mode (openai-whisper).

Whisper runs on the machine, so a retiring engineer's Hindi or English voice note
never leaves the plant. The model is loaded once and cached because loading is the
slow part, not transcription. Everything here fails loudly with a clear message
rather than crashing, so the endpoint can fall back to a typed transcript and the
demo never hard-depends on audio working in a noisy room.
"""

import logging
from functools import lru_cache

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class Transcription(BaseModel):
    text: str
    language: str


@lru_cache
def _load_model():
    """Load and cache the Whisper model once. Imported lazily so a missing Whisper
    install does not break app startup, only the audio path."""
    import whisper  # local import: heavy, and optional if only the text path is used

    logger.info("Loading Whisper model '%s' (first call is slow)...", settings.WHISPER_MODEL)
    return whisper.load_model(settings.WHISPER_MODEL)


def transcribe(audio_path: str) -> Transcription:
    """
    Transcribe an audio file to text, auto-detecting Hindi or English.

    Raises RuntimeError with a readable message if Whisper is unavailable or the
    audio cannot be read (usually a missing ffmpeg), so the caller can fall back
    to a typed transcript.
    """
    try:
        model = _load_model()
        result = model.transcribe(audio_path)
    except Exception as exc:
        raise RuntimeError(f"Transcription failed ({exc}). Use the text transcript fallback.") from exc

    return Transcription(text=(result.get("text") or "").strip(), language=result.get("language", "unknown"))
