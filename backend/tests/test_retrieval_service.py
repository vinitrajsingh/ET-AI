"""
Retrieval layer against live Qdrant + graph. Uses embeddings (cheap), no chat LLM.
Skips if the corpus isn't seeded.
"""

import pytest

from app.services.retrieval_service import (
    gather_graph_context,
    resolve_equipment_in_query,
    vector_search,
)


def _require_seed():
    if gather_graph_context("P-101") is None:
        pytest.skip("Graph not seeded; run POST /ingest/bulk first")


def test_vector_search_returns_p101_related_chunks():
    _require_seed()
    doc_ids = gather_graph_context("P-101").doc_ids
    hits = vector_search("bearing lubrication", equipment_tag="P-101", doc_ids=doc_ids)

    assert hits, "vector search returned nothing"
    # At least one chunk should belong to a document the graph links to P-101.
    assert any(h.doc_id in doc_ids for h in hits)


def test_resolve_equipment_in_query():
    assert resolve_equipment_in_query("what's wrong with P-101?") == "P-101"
    assert resolve_equipment_in_query("tell me about the plant") is None
