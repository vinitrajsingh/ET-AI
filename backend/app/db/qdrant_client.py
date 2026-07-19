"""
Qdrant client (the vector store for semantic / RAG search).

Qdrant stores document *chunks* as high-dimensional vectors (embeddings) plus a
JSON payload (source doc, page, equipment tag). At query time we embed the
question and ask Qdrant for the nearest vectors — that's semantic search. Like
Neo4j, we keep one client for the whole app.

`ensure_collection()` is idempotent: it creates the collection only if missing,
so it's safe to call on every startup.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    """Return the shared Qdrant client, creating it on first use (singleton)."""
    global _client
    if _client is None:
        # url points at the local Docker container (http://localhost:6333).
        _client = QdrantClient(url=settings.QDRANT_URL)
    return _client


def ensure_collection() -> None:
    """
    Create the default collection if it does not already exist.
    COSINE distance pairs with OpenAI's normalized embeddings; size must match
    the embedding model's dimension (1536 for text-embedding-3-small).
    """
    client = get_qdrant()
    existing = {c.name for c in client.get_collections().collections}
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def ping_qdrant() -> bool:
    """Health check: list collections (round-trips to the server)."""
    get_qdrant().get_collections()
    return True
