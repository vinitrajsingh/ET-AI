"""
Asset register connector: links equipment to the manual and regulation PDFs that
apply to it.

Generic OEM manuals and OISD/Factory Act documents never mention specific plant
tags, so entity extraction cannot connect them to equipment. A real plant instead
keeps an asset register (which manual belongs to which pump, which regulations
govern which vessel). We model that as a small JSON file (data/asset_register.json)
and MERGE the edges here:

    Equipment -[:HAS_MANUAL]->   Document   (the OEM manual PDF)
    Equipment -[:GOVERNED_BY]->  Document   (the regulation PDF)

Run after ingestion so both the Equipment and Document nodes already exist. It is
idempotent (MERGE) and validates the mapping against what is actually in the graph,
warning about any tag or doc_id that does not resolve.
"""

import json
import logging
from pathlib import Path

from app.config import settings
from app.db.neo4j_client import get_driver
from app.db.schema import Node, Rel, merge_key

logger = logging.getLogger(__name__)

# Only these relationship types may be declared in the register file.
_ALLOWED = {"HAS_MANUAL": Rel.HAS_MANUAL, "GOVERNED_BY": Rel.GOVERNED_BY}


def load_register(path: str | Path | None = None) -> dict:
    """Read the asset-register JSON, ignoring comment keys (starting with '_')."""
    path = Path(path or settings.ASSET_REGISTER)
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def link_asset_register(path: str | Path | None = None) -> dict:
    """
    Create the curated edges. Returns a summary: how many of each edge type were
    newly created, plus any mapping entries that did not match a real node.
    """
    register = load_register(path)
    created: dict[str, int] = {}
    skipped: list[str] = []

    with get_driver().session() as session:
        known_tags = _existing_values(session, Node.EQUIPMENT)
        known_docs = _existing_values(session, Node.DOCUMENT)

        for rel_name, mapping in register.items():
            rel = _ALLOWED.get(rel_name)
            if rel is None:
                skipped.append(f"unknown relationship '{rel_name}' in register")
                continue

            created[rel_name] = 0
            for tag, doc_ids in mapping.items():
                if tag not in known_tags:
                    skipped.append(f"{rel_name}: equipment '{tag}' not in graph")
                    continue
                for doc_id in doc_ids:
                    if doc_id not in known_docs:
                        skipped.append(f"{rel_name}: document '{doc_id}' not in graph")
                        continue
                    created[rel_name] += _merge_edge(session, tag, rel, doc_id)

    return {"created": created, "skipped": skipped}


def _existing_values(session, node: Node) -> set[str]:
    """Fetch the set of MERGE-key values already present for a node label."""
    key = merge_key(node)
    rows = session.run(f"MATCH (n:{node.value}) RETURN n.{key} AS v")
    return {r["v"] for r in rows if r["v"] is not None}


def _merge_edge(session, tag: str, rel: Rel, doc_id: str) -> int:
    """MERGE one Equipment -> Document edge. Returns 1 if newly created."""
    cypher = (
        "MATCH (e:Equipment {tag: $tag}) "
        "MATCH (d:Document {doc_id: $doc_id}) "
        f"MERGE (e)-[r:{rel.value}]->(d)"
    )
    summary = session.run(cypher, tag=tag, doc_id=doc_id).consume()
    return summary.counters.relationships_created
