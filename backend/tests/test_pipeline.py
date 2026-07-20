"""
End-to-end: ingesting one corpus file creates graph nodes and vector chunks.

Uses the work-order sheet (small, cheap to embed) and touches all three systems:
Neo4j (nodes), OpenAI (embeddings), Qdrant (chunks). Requires live services.
"""

from app.ingestion.pipeline import ingest_file


def test_ingest_file_creates_nodes_and_chunks(workorders_xlsx):
    summary = ingest_file(workorders_xlsx, embed=True)

    assert summary.nodes_total > 0, "No graph nodes were written"
    assert summary.entity_counts["work_orders"] > 0, "No work orders extracted"
    assert summary.chunks_embedded > 0, "No chunks embedded into Qdrant"
