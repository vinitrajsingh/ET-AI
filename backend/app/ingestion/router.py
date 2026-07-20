"""
Extractor router: pick the right extractor for a file by its extension.

This is the only place that knows the mapping from file type to extractor, so
adding a new format later is a one-line change. Images are split by a filename
hint: P&ID drawings go to the vision extractor, everything else to OCR.
"""

from pathlib import Path
from typing import Callable

from app.ingestion.extractors import docx, email, excel, image, pdf, pid
from app.ingestion.extractors.base import ExtractedContent

Extractor = Callable[[str | Path], ExtractedContent]

_BY_EXTENSION: dict[str, Extractor] = {
    ".pdf": pdf.extract,
    ".docx": docx.extract,
    ".xlsx": excel.extract,
    ".xls": excel.extract,
    ".eml": email.extract,
}

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def get_extractor(path: str | Path) -> Extractor:
    """Return the extractor for this file, or raise if the type is unsupported."""
    path = Path(path)
    ext = path.suffix.lower()

    if ext in _BY_EXTENSION:
        return _BY_EXTENSION[ext]

    if ext in _IMAGE_EXTENSIONS:
        # P&ID drawings are named like PID_..._P-101_...; treat those as diagrams
        # (vision) and any other image as a scan to OCR.
        return pid.extract if _looks_like_pid(path.name) else image.extract

    raise ValueError(f"Unsupported file type: {ext} ({path.name})")


def _looks_like_pid(name: str) -> bool:
    lowered = name.lower()
    return "pid" in lowered or "p&id" in lowered or "dwg" in lowered
