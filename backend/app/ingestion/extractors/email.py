"""
Email extractor.

Parses .eml files with the Python standard library. We keep the useful headers
(from, to, date, subject) and the plain-text body, flattening them into one text
block so a mail thread reads like any other document downstream.
"""

from email import policy
from email.parser import BytesParser
from pathlib import Path

from app.ingestion.extractors.base import ExtractedContent, find_equipment_tags


def extract(path: str | Path) -> ExtractedContent:
    with open(path, "rb") as fh:
        msg = BytesParser(policy=policy.default).parse(fh)

    header_lines = [
        f"From: {msg.get('from', '')}",
        f"To: {msg.get('to', '')}",
        f"Date: {msg.get('date', '')}",
        f"Subject: {msg.get('subject', '')}",
    ]
    text = "\n".join(header_lines) + "\n\n" + _body(msg)
    content = ExtractedContent(text=text.strip(), doc_type="email")
    content.equipment_tags = find_equipment_tags(text)
    return content


def _body(msg) -> str:
    """Pull the plain-text body, walking multipart messages if needed."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content()
        return ""
    return msg.get_content()
