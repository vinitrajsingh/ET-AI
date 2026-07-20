"""
PDF extractor.

PyMuPDF (fitz) does the heavy lifting: it pulls text out of digital PDFs fast and
reliably, which is what our manuals, regulations, and incident reports are. We
walk the pages, join their text, and hand it back. Docling is the intended path
for messy scans and table-heavy layouts; it is imported lazily so a missing (or
still-installing) Docling never blocks ingestion of the ordinary PDFs.
"""

from pathlib import Path

import fitz

from app.ingestion.extractors.base import ExtractedContent, find_equipment_tags


def extract(path: str | Path) -> ExtractedContent:
    path = Path(path)
    pages: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))

    text = "\n".join(pages).strip()
    content = ExtractedContent(text=text, doc_type=_guess_type(path))
    content.equipment_tags = find_equipment_tags(text)
    if not text:
        # A scanned PDF with no text layer would land here. Flag it so the demo
        # operator knows to enable Docling OCR rather than silently getting nothing.
        content.warnings.append("No extractable text; this PDF may be scanned (needs OCR).")
    return content


def _guess_type(path: Path) -> str:
    """Use the corpus folder name as a hint for the document's role."""
    parent = path.parent.name.lower()
    if "incident" in parent:
        return "incident"
    if "regulation" in parent:
        return "regulation"
    if "manual" in parent:
        return "manual"
    return "document"
