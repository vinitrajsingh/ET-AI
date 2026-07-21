"""
Graph verification: run a handful of read-only checks and print them, so you can
confirm the graph matches expectations before building retrieval on top of it.

    python -m scripts.verify_graph        (from the backend/ folder, venv active)

Read-only. The equivalent raw Cypher is in scripts/verify.cypher for pasting into
the Neo4j Browser.
"""

from app.db.neo4j_client import get_driver

# (heading, cypher) pairs. Kept as data so adding a check is a one-line edit.
CHECKS: list[tuple[str, str]] = [
    ("Node counts by label",
     "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC"),
    ("Relationship counts by type",
     "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS count ORDER BY count DESC"),
    ("Equipment -> work-order counts",
     "MATCH (e:Equipment) OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w) "
     "RETURN e.tag AS equipment, count(w) AS work_orders ORDER BY equipment"),
    ("Equipment -> incidents",
     "MATCH (e:Equipment)-[:HAS_INCIDENT]->(i) RETURN e.tag AS equipment, i.id AS incident"),
    ("Equipment -> manuals",
     "MATCH (e:Equipment)-[:HAS_MANUAL]->(d) RETURN e.tag AS equipment, d.title AS manual"),
    ("Equipment -> governing regulations",
     "MATCH (e:Equipment)-[:GOVERNED_BY]->(d) "
     "RETURN e.tag AS equipment, collect(d.title) AS governed_by ORDER BY equipment"),
    ("Equipment outgoing relationship types",
     "MATCH (e:Equipment)-[r]->() RETURN e.tag AS equipment, collect(DISTINCT type(r)) AS rels ORDER BY equipment"),
    ("Documents by type",
     "MATCH (d:Document) RETURN d.type AS type, count(*) AS count ORDER BY count DESC"),
]


def run() -> None:
    with get_driver().session() as session:
        for title, cypher in CHECKS:
            print(f"\n=== {title} ===")
            for record in session.run(cypher):
                print("  " + "  ".join(f"{k}={record[k]}" for k in record.keys()))


if __name__ == "__main__":
    run()
