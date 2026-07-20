"""
Stage 6: embed chunks and store them in Qdrant.

Each chunk becomes a point: the vector for search, plus a payload that traces the
chunk back to its equipment and source document. That metadata is what lets the
copilot later cite "manual page / work order / incident" and jump to the exact
source. Point ids are deterministic (doc_id + chunk index) so re-ingesting a
document overwrites its old chunks instead of piling up duplicates.
"""

import uuid

from qdrant_client.models import PointStruct

from app.config import settings
from app.db.qdrant_client import ensure_collection, get_qdrant
from app.services.embeddings import embed_texts

# Stable namespace so the same (doc_id, chunk_index) always yields the same id.
_ID_NAMESPACE = uuid.UUID("5a9e1b7c-0000-4000-8000-000000000001")


def embed_and_store(chunks: list[str], metadata: dict) -> int:
    """Embed chunks and upsert them into Qdrant. Returns the number stored."""
    if not chunks:
        return 0

    ensure_collection()  # cheap and idempotent; makes this safe to call standalone
    vectors = embed_texts(chunks)

    doc_id = metadata.get("doc_id", "unknown")
    points = [
        PointStruct(
            id=str(uuid.uuid5(_ID_NAMESPACE, f"{doc_id}:{i}")),
            vector=vector,
            payload={**metadata, "chunk_index": i, "text": chunk},
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    get_qdrant().upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return len(points)
