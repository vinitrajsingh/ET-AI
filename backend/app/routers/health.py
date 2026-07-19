"""
Health router — one endpoint that pings all three databases.

GET /health returns {status, neo4j, qdrant, postgres}. Each DB field is "ok" or
"error: <reason>". `status` is "ok" only if all three are reachable, else
"degraded". This lets you verify every connection with a single curl once .env
is filled in.
"""

from fastapi import APIRouter

from app.db.neo4j_client import ping_neo4j
from app.db.postgres import ping_postgres
from app.db.qdrant_client import ping_qdrant

router = APIRouter(tags=["health"])


def _check(ping) -> str:
    """Run a ping function, returning 'ok' or a short error string."""
    try:
        ping()
        return "ok"
    except Exception as exc:  # surface the real reason, don't hide it
        return f"error: {exc}"


@router.get("/health")
def health():
    neo4j = _check(ping_neo4j)
    qdrant = _check(ping_qdrant)
    postgres = _check(ping_postgres)
    all_ok = all(v == "ok" for v in (neo4j, qdrant, postgres))
    return {
        "status": "ok" if all_ok else "degraded",
        "neo4j": neo4j,
        "qdrant": qdrant,
        "postgres": postgres,
    }
