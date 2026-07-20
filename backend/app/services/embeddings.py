"""
Embeddings service: text -> vectors via OpenAI text-embedding-3-small (1536-dim).

Isolated from the chat LLM so the vector model can change without touching the
rest of the pipeline. Batches inputs because embedding one string per request is
slow and wasteful.
"""

from app.config import settings
from app.services.llm import get_client


def embed_texts(texts: list[str], batch_size: int = 128) -> list[list[float]]:
    """Embed many strings, returning one vector per input in the same order."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        resp = get_client().embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in resp.data)
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string (used later by the copilot)."""
    return embed_texts([text])[0]
