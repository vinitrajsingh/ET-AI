"""
P&ID drawing extractor.

A P&ID is an image, so there is no text to parse. Two sources of truth:

  1. The filename, which in this corpus reliably encodes the primary tag
     (PID_DWG-2101_P-101_CrudeFeedPump.png -> P-101). This is the dependable
     signal and never costs an API call.
  2. A vision-model pass that reads the drawing and reports the equipment and
     connections it sees. This enriches the description for search but is
     optional: it can be turned off (config) or skipped in tests.
"""

import base64
import re
from pathlib import Path

from app.config import settings
from app.ingestion.extractors.base import ExtractedContent, find_equipment_tags

_VISION_PROMPT = (
    "This is a Piping & Instrumentation Diagram (P&ID) from an oil refinery. "
    "List the equipment tags shown (like P-101, C-201, HX-301), what each item is, "
    "and how they connect (which lines run between which equipment). "
    "Keep it concise and factual."
)


def extract(path: str | Path, use_vision: bool | None = None) -> ExtractedContent:
    path = Path(path)
    tags = _tags_from_filename(path.name)

    content = ExtractedContent(doc_type="pid", equipment_tags=tags)
    content.text = f"P&ID drawing {path.stem}. Equipment: {', '.join(tags) or 'unspecified'}."

    if use_vision is None:
        use_vision = settings.USE_PID_VISION
    if use_vision:
        _add_vision_description(path, content)

    return content


def _tags_from_filename(name: str) -> list[str]:
    """Extract equipment tags from the drawing filename (the reliable signal)."""
    return find_equipment_tags(name)


def _add_vision_description(path: Path, content: ExtractedContent) -> None:
    """Best-effort vision pass; a failure here must not fail the ingest."""
    from app.services.llm import describe_image  # local import keeps OpenAI cost out of imports

    try:
        b64 = base64.b64encode(path.read_bytes()).decode()
        description = describe_image(_VISION_PROMPT, b64)
        content.text = f"{content.text}\n\n{description}".strip()
        # Merge any tags the model spotted that the filename missed.
        for tag in find_equipment_tags(description):
            if tag not in content.equipment_tags:
                content.equipment_tags.append(tag)
    except Exception as exc:
        content.warnings.append(f"P&ID vision read failed: {exc}")
