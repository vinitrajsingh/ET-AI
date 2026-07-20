"""
Excel extractor.

Spreadsheets are the one place where we trust the structure completely, so we
read every sheet into row dicts with pandas and pass them through untouched. The
work-order sheet is the backbone of the prediction demo; sending it through an
LLM would only add errors, so later stages parse these rows directly.

We also build a plain-text rendering of the rows so each work order still gets
embedded and becomes searchable by the copilot.
"""

from pathlib import Path

import pandas as pd

from app.ingestion.extractors.base import ExtractedContent


def extract(path: str | Path) -> ExtractedContent:
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)  # dtype=str: keep ids/dates verbatim

    tables: list[list[dict]] = []
    text_blocks: list[str] = []
    for name, df in sheets.items():
        df = df.where(df.notna(), None)  # NaN -> None so JSON/graph stay clean
        rows = df.to_dict(orient="records")
        tables.append(rows)
        text_blocks.append(_rows_to_text(name, rows))

    doc_type = "workorders" if _looks_like_workorders(tables) else "spreadsheet"
    return ExtractedContent(text="\n\n".join(text_blocks), tables=tables, doc_type=doc_type)


def _rows_to_text(sheet_name: str, rows: list[dict]) -> str:
    """One readable line per row, so each record embeds as its own searchable unit."""
    lines = [f"[{sheet_name}]"]
    for row in rows:
        parts = [f"{k}: {v}" for k, v in row.items() if v not in (None, "")]
        lines.append("; ".join(parts))
    return "\n".join(lines)


def _looks_like_workorders(tables: list[list[dict]]) -> bool:
    for rows in tables:
        if rows and {"wo_id", "equipment_tag"} <= set(rows[0].keys()):
            return True
    return False
