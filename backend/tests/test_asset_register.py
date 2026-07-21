"""
The asset-register connector links equipment to the right manual/regulation PDFs.

Runs against the seeded graph (equipment + document nodes must already exist);
skips cleanly if they don't, so it never fails on an empty database.
"""

import pytest

from app.db.neo4j_client import get_driver
from app.ingestion.asset_register import link_asset_register


def _has_edge(cypher: str, **params) -> bool:
    with get_driver().session() as session:
        return session.run(cypher, **params).single() is not None


def test_connector_links_manual_and_regulation():
    if not _has_edge("MATCH (e:Equipment {tag:'P-101'}) RETURN e"):
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")

    result = link_asset_register()
    assert not any("not in graph" in s for s in result["skipped"]), result["skipped"]

    assert _has_edge(
        "MATCH (:Equipment {tag:'P-101'})-[:HAS_MANUAL]->(d:Document) RETURN d"
    ), "P-101 should link to its OEM manual"
    assert _has_edge(
        "MATCH (:Equipment {tag:'T-205'})-[:GOVERNED_BY]->(:Document {doc_id:'OISD-STD-105'}) RETURN 1"
    ), "T-205 should be governed by OISD-STD-105"
