"""
Neo4j AuraDB client (the knowledge graph).

Neo4j is a graph database: instead of tables/rows it stores *nodes* (e.g. an
Equipment "P-101") and *relationships* between them (e.g. P-101 -[:HAS_INCIDENT]->
INC-2023-41). We hold ONE driver for the whole app — the driver is a connection
pool and is safe to share across requests. Each unit of work opens a short-lived
`session` from that pool.

Usage:
    from app.db.neo4j_client import get_driver, ping_neo4j
    with get_driver().session() as session:
        session.run("MATCH (n) RETURN n LIMIT 1")
"""

from neo4j import Driver, GraphDatabase

from app.config import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the shared Neo4j driver, creating it on first use (singleton)."""
    global _driver
    if _driver is None:
        # AuraDB URIs use neo4j+s:// which already implies encryption, so we do
        # NOT pass encrypted=/trust= here (doing so would raise a config error).
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def ping_neo4j() -> bool:
    """
    Health check: run a trivial query and confirm it returns.
    Returns True on success; raises the underlying exception on failure so the
    /health endpoint can report the real reason.
    """
    with get_driver().session() as session:
        result = session.run("RETURN 1 AS ok")
        return result.single()["ok"] == 1


def close_driver() -> None:
    """Close the pool on app shutdown."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
