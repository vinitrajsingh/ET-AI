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
    LLM_MODEL: str = Field("gpt-4o-mini", description="Default chat model (entity extraction)")
    VISION_MODEL: str = Field("gpt-4o", description="Vision model for reading P&ID drawings")

    # --- Ingestion tuning ---
    # Where the demo corpus lives, relative to the backend/ working directory.
    DATA_DIR: str = Field("data/corpus_full", description="Root folder of the demo corpus")
    CHUNK_SIZE: int = Field(1000, description="Approx characters per embedding chunk")
    CHUNK_OVERLAP: int = Field(150, description="Character overlap between adjacent chunks")
    # Guard against embedding an entire 200-page report during a demo seed.
    MAX_CHUNKS_PER_DOC: int = Field(200, description="Cap on chunks embedded per document")
    USE_PID_VISION: bool = Field(True, description="Call the vision model on P&ID drawings")
    # The fictional plant's asset register. Tag-like strings in generic manuals
    # and regulations (e.g. "P-11", "T-101") match our pattern but are not real
    # assets, so we keep only these as Equipment nodes.
    KNOWN_EQUIPMENT: str = Field(
        "P-101,C-201,T-205,HX-301,B-7",
        description="Comma-separated canonical equipment tags for Bharat Petrochem Unit-2",
    )

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
