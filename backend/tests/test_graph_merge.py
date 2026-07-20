"""
Stage 4: MERGE is idempotent. Ingesting the same file twice must NOT create a
second P-101. This is the core anti-duplication guarantee of the whole project.

Requires a live Neo4j (AuraDB). Embedding is skipped to keep the test fast.
"""

from app.db.neo4j_client import get_driver
from app.ingestion.pipeline import ingest_file


def _equipment_count(tag: str) -> int:
    with get_driver().session() as session:
        result = session.run(
            "MATCH (e:Equipment {tag: $tag}) RETURN count(e) AS n", tag=tag
        )
        return result.single()["n"]


def test_reingest_does_not_duplicate_equipment(workorders_xlsx):
    ingest_file(workorders_xlsx, embed=False)
    ingest_file(workorders_xlsx, embed=False)

    assert _equipment_count("P-101") == 1, "MERGE created a duplicate Equipment node"
