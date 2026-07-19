"""
Central configuration for the SANJEEVANI backend.

Loads and validates every secret/connection string from a local `.env` file
using pydantic-settings. Import the singleton `settings` anywhere in the app
instead of reading os.environ directly, so there is exactly one validated
source of truth. If a required variable is missing, the app fails fast at
startup with a clear error rather than at first use.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- OpenAI (embeddings + chat) ---
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key (sk-...)")

    # --- Neo4j AuraDB (knowledge graph) ---
    # URI looks like: neo4j+s://xxxx.databases.neo4j.io  (the +s = TLS)
    NEO4J_URI: str = Field(..., description="Neo4j AuraDB bolt URI")
    NEO4J_USER: str = Field("neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")

    # --- Qdrant (vector store, local Docker) ---
    QDRANT_URL: str = Field("http://localhost:6333", description="Qdrant HTTP URL")

    # --- Neon Postgres (structured data) ---
    # Neon requires SSL. Use a URL like:
    # postgresql+psycopg2://user:pass@host/db?sslmode=require
    DATABASE_URL: str = Field(..., description="Neon Postgres SQLAlchemy URL (sslmode=require)")

    # --- App defaults (safe to leave as-is) ---
    FRONTEND_ORIGIN: str = Field("http://localhost:3000", description="CORS origin for the Next.js app")
    QDRANT_COLLECTION: str = Field("sanjeevani_chunks", description="Default vector collection name")
    EMBEDDING_MODEL: str = Field("text-embedding-3-small", description="OpenAI embeddings model")
    EMBEDDING_DIM: int = Field(1536, description="Vector size for text-embedding-3-small")
    LLM_MODEL: str = Field("gpt-4o-mini", description="Default chat model")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars instead of erroring
    )


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env is parsed/validated only once per process."""
    return Settings()


# Import this everywhere: `from app.config import settings`
settings = get_settings()
