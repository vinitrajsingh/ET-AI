"""
Stage 1 of the pipeline: file -> clean text (+ tables).

Thin entry point that delegates to the right extractor via the router. Kept
separate from the router so the pipeline depends on a stable function name while
the routing logic can evolve behind it.
"""

from pathlib import Path

from app.ingestion.extractors.base import ExtractedContent
from app.ingestion.router import get_extractor


def extract_text(path: str | Path) -> ExtractedContent:
    """Extract normalized content from a single file, whatever its type."""
    extractor = get_extractor(path)
    return extractor(path)
