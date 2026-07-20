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

import certifi
import neo4j
from neo4j import Driver, GraphDatabase

from app.config import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the shared Neo4j driver, creating it on first use (singleton)."""
    global _driver
    if _driver is None:
        _driver = _build_driver()
    return _driver


def _build_driver() -> Driver:
    """
    Build the driver with an explicit CA bundle.

    Aura's certificate is signed by a CA that is present in certifi but missing
    from some Windows system trust stores. The default neo4j+s:// path uses the
    system store, so on those machines the TLS handshake fails and the driver
    reports the misleading "Unable to retrieve routing information". To avoid
    that, we rebuild the connection on the base scheme and hand the driver
    certifi's bundle, which verifies Aura's cert everywhere.
    """
    uri = settings.NEO4J_URI
    auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)

    if uri.startswith(("neo4j+s://", "bolt+s://")):
        base = uri.replace("+s://", "://", 1)
        return GraphDatabase.driver(
            base, auth=auth, encrypted=True,
            trusted_certificates=neo4j.TrustCustomCAs(certifi.where()),
        )
    if uri.startswith(("neo4j+ssc://", "bolt+ssc://")):
        base = uri.replace("+ssc://", "://", 1)
        return GraphDatabase.driver(base, auth=auth, encrypted=True, trusted_certificates=neo4j.TrustAll())

    # Plain neo4j:// / bolt:// (e.g. a local, unencrypted instance): use as-is.
    return GraphDatabase.driver(uri, auth=auth)


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
