"""
Image (OCR) extractor for scanned forms and photos.

Real scans have no text layer, so we run OCR via Docling. Docling pulls in heavy
model dependencies, so it is imported lazily: if it is not installed the pipeline
keeps working and simply warns that this one image could not be read. P&ID
drawings are handled separately in pid.py (vision, not OCR).
"""

from pathlib import Path

from app.ingestion.extractors.base import ExtractedContent, find_equipment_tags


def extract(path: str | Path) -> ExtractedContent:
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        return ExtractedContent(
            doc_type="image",
            warnings=["Docling not installed; skipped OCR for this image."],
        )

    result = DocumentConverter().convert(str(path))
    text = result.document.export_to_markdown().strip()
    content = ExtractedContent(text=text, doc_type="image")
    content.equipment_tags = find_equipment_tags(text)
    return content
