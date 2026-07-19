"""
Neon Postgres via SQLAlchemy (structured/relational data).

Holds the classic tables: users, equipment, work orders, permits, incidents,
guru notes. We expose:
  - `engine`   : the connection pool (one per process)
  - `SessionLocal` : a factory for short-lived DB sessions (one per request)
  - `Base`     : the declarative base every model in app/models inherits from
  - `get_db()` : FastAPI dependency that yields a session and always closes it

Neon (serverless Postgres) REQUIRES SSL. We enforce `sslmode=require` on the
connection string even if the user forgot to add it, so connections don't fail.
"""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _with_sslmode_require(url: str) -> str:
    """Ensure the Neon URL carries sslmode=require (add it if absent)."""
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.setdefault("sslmode", "require")
    return urlunparse(parts._replace(query=urlencode(query)))


# pool_pre_ping recycles dead connections — important for Neon, which may put an
# idle serverless endpoint to sleep and drop the socket.
engine = create_engine(
    _with_sslmode_require(settings.DATABASE_URL),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models (see app/models)."""


def get_db():
    """FastAPI dependency: yield a session, guarantee it's closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_postgres() -> bool:
    """Health check: open a connection and run SELECT 1."""
    with engine.connect() as conn:
        return conn.execute(text("SELECT 1")).scalar() == 1
