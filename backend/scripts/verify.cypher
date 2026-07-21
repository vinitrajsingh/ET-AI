// SANJEEVANI graph verification queries.
// Paste any of these into the Neo4j Browser (console.neo4j.io -> Query).
// Note: Document nodes use `title` and `type` (not `name`).

// 1. How many of each node type?
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// 2. How many of each relationship type?
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS count ORDER BY count DESC;

// 3. Each equipment with its work-order count.
MATCH (e:Equipment)
OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w)
RETURN e.tag, count(w) ORDER BY e.tag;

// 4. Equipment -> incidents (the T-205 near-miss should appear).
MATCH (e:Equipment)-[:HAS_INCIDENT]->(i) RETURN e.tag, i.id;

// 5. Equipment -> manual PDFs (from the asset register).
MATCH (e:Equipment)-[:HAS_MANUAL]->(d) RETURN e.tag, d.title;

// 6. Equipment -> governing regulation PDFs (from the asset register).
MATCH (e:Equipment)-[:GOVERNED_BY]->(d) RETURN e.tag, collect(d.title) ORDER BY e.tag;

// 7. What documents exist, by type.
MATCH (d:Document) RETURN d.title, d.type ORDER BY d.type;

// 8. All outgoing relationship types per equipment.
MATCH (e:Equipment)-[r]->() RETURN e.tag, collect(DISTINCT type(r)) ORDER BY e.tag;

// 9. Visualize P-101's full neighbourhood (great for a screenshot).
MATCH p=(e:Equipment {tag:'P-101'})-[r]-(n) RETURN p;
