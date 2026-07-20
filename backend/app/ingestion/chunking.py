"""
Stage 5: split text into overlapping chunks for embedding.

A plain sliding window over characters, but we nudge each cut to the nearest
whitespace so we do not slice through the middle of a word. Overlap keeps context
from being lost at chunk boundaries. `max_chunks` is a safety valve so a single
200-page report cannot flood the vector store during a demo seed.
"""

from app.config import settings


def chunk_text(
    text: str,
    size: int | None = None,
    overlap: int | None = None,
    max_chunks: int | None = None,
) -> list[str]:
    size = size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    max_chunks = max_chunks or settings.MAX_CHUNKS_PER_DOC

    text = (text or "").strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n and len(chunks) < max_chunks:
        end = min(start + size, n)
        end = _snap_to_whitespace(text, end, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)  # step forward, keep the overlap

    return chunks


def _snap_to_whitespace(text: str, end: int, n: int, window: int = 100) -> int:
    """Move the cut back to the last whitespace within `window` chars, if any."""
    if end >= n:
        return n
    space = text.rfind(" ", end - window, end)
    newline = text.rfind("\n", end - window, end)
    cut = max(space, newline)
    return cut if cut > 0 else end
