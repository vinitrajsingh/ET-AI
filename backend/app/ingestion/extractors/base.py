"""
Shared types for the extractor layer.

Every extractor returns an ExtractedContent so the rest of the pipeline does not
care which file type it came from. Kept dependency-free on purpose so extractors
can import it without any circular-import risk.
"""

import re

from pydantic import BaseModel, Field


class ExtractedContent(BaseModel):
    """Normalized output of stage 1 (text extraction) for any file."""

    text: str = ""
    # Each table is a list of row dicts (column name -> value). Structured files
    # like the work-order Excel land here and skip the LLM in later stages.
    tables: list[list[dict]] = Field(default_factory=list)
    doc_type: str = "document"  # document | workorders | pid | manual | regulation | incident | email
    # Equipment tags we are confident about from the source itself (e.g. a P&ID
    # filename), independent of anything the LLM later infers.
    equipment_tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# Bharat Petrochem Unit-2 tag prefixes. Deliberately tight so drawing numbers
# like DWG-2101 are NOT mistaken for equipment tags. HX is listed first so the
# two-letter prefix wins over a single letter during matching.
EQUIPMENT_TAG_RE = re.compile(r"\b(?:HX|P|C|T|B)-\d{1,4}\b")


def find_equipment_tags(text: str) -> list[str]:
    """Return unique equipment tags found in text, preserving first-seen order."""
    seen: list[str] = []
    for m in EQUIPMENT_TAG_RE.findall(text or ""):
        if m not in seen:
            seen.append(m)
    return seen
