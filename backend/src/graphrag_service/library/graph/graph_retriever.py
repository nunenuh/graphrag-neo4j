"""Graph-only retrieval via Cypher queries.

Generates and executes Cypher queries based on query type and extracted entities.
"""

from loguru import logger


# Cypher templates for each query type that uses GRAPH_ONLY strategy
CYPHER_TEMPLATES: dict[str, str] = {
    "FACTUAL_LOOKUP": """
        MATCH (n)
        WHERE n.name =~ $pattern OR n.title =~ $pattern
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, labels(n)[0] AS label,
               collect(DISTINCT {
                   from: n.uid, to: m.uid, type: type(r),
                   props: properties(r)
               })[..20] AS edges,
               collect(DISTINCT {node: m, label: labels(m)[0]})[..20] AS neighbors
        LIMIT 5
    """,
    "TEMPORAL": """
        MATCH (m:Method)-[e:EVALUATED_ON]->(d:Dataset)
        WHERE (m.name =~ $pattern OR d.name =~ $pattern)
        RETURN m, d, e, labels(m)[0] AS m_label, labels(d)[0] AS d_label
        ORDER BY e.year DESC
        LIMIT 20
    """,
    "AGGREGATION": """
        MATCH (n)
        WHERE n.name =~ $pattern OR n.title =~ $pattern
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, labels(n)[0] AS label, count(DISTINCT m) AS neighbor_count,
               collect(DISTINCT {
                   from: n.uid, to: m.uid, type: type(r),
                   props: properties(r)
               })[..20] AS edges,
               collect(DISTINCT {node: m, label: labels(m)[0]})[..20] AS neighbors
        LIMIT 10
    """,
    "NETWORK": """
        MATCH (a:Author)-[:AUTHORED]->(p:Paper)
        WHERE a.name =~ $pattern
           OR p.title =~ $pattern
        OPTIONAL MATCH (p)<-[:AUTHORED]-(coauthor:Author)
        WHERE coauthor <> a
        OPTIONAL MATCH (p)-[:ADDRESSES_TASK]->(t:Task)
        OPTIONAL MATCH (p)-[:USES_METHOD]->(m:Method)
        RETURN a, labels(a)[0] AS a_label, p, labels(p)[0] AS p_label,
               collect(DISTINCT coauthor)[..10] AS coauthors,
               collect(DISTINCT t.name)[..10] AS tasks,
               collect(DISTINCT m.name)[..10] AS methods
        LIMIT 10
    """,
}

# Fallback for unknown types
FALLBACK_TEMPLATE = """
    MATCH (n)
    WHERE n.name =~ $pattern OR n.title =~ $pattern
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN n, labels(n)[0] AS label,
           collect(DISTINCT {
               from: n.uid, to: m.uid, type: type(r),
               props: properties(r)
           })[..20] AS edges,
           collect(DISTINCT {node: m, label: labels(m)[0]})[..20] AS neighbors
    LIMIT 5
"""


def _build_pattern(entities: list[str]) -> str:
    """Build a case-insensitive regex pattern from entity list."""
    if not entities:
        return ".*"
    escaped = [e.replace("(", "\\(").replace(")", "\\)") for e in entities]
    return "(?i).*(" + "|".join(escaped) + ").*"


def graph_retrieve(
    query_type: str,
    entities: list[str],
    run_cypher_fn: callable,
) -> tuple[dict[str, dict], list[dict]]:
    """Execute graph-only retrieval using Cypher templates.

    Args:
        query_type: Classified query type.
        entities: Extracted entities from classifier.
        run_cypher_fn: Callable to execute Cypher (client.run_query).

    Returns:
        Tuple of (nodes_by_id, edges_list) matching traversal format.
    """
    template = CYPHER_TEMPLATES.get(query_type, FALLBACK_TEMPLATE)
    pattern = _build_pattern(entities)

    logger.bind(query_type=query_type, pattern=pattern).info("graph_retrieve.start")

    try:
        rows = run_cypher_fn(template, {"pattern": pattern})
    except Exception as e:
        logger.bind(error=str(e)).error("graph_retrieve.failed")
        return {}, []

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for row in rows:
        # Process main node 'n' or named nodes
        for key in ("n", "m", "a", "p", "d"):
            node = row.get(key)
            if node is None:
                continue
            d = {k: v for k, v in dict(node).items() if k != "embedding"}
            label_key = f"{key}_label" if key != "n" else "label"
            d["label"] = row.get(label_key, "")
            d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
            if d.get("uid"):
                nodes[d["uid"]] = d

        # Process neighbor nodes
        for wrapped in row.get("neighbors", []) or []:
            if not isinstance(wrapped, dict):
                continue
            node = wrapped.get("node")
            if node is None:
                continue
            d = {k: v for k, v in dict(node).items() if k != "embedding"}
            d["label"] = wrapped.get("label", "")
            d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
            if d.get("uid"):
                nodes[d["uid"]] = d

        # Process coauthors
        for coauthor in row.get("coauthors", []) or []:
            if coauthor is None:
                continue
            d = {k: v for k, v in dict(coauthor).items() if k != "embedding"}
            d["label"] = "Author"
            d["name"] = d.get("name") or d.get("uid", "")
            if d.get("uid"):
                nodes[d["uid"]] = d

        # Process edges
        for e in row.get("edges", []) or []:
            if isinstance(e, dict) and e.get("from") and e.get("to") and e.get("type"):
                edges.append({
                    "from_id": e["from"],
                    "to_id": e["to"],
                    "type": e["type"],
                    "properties": dict(e.get("props") or {}),
                })

    logger.bind(nodes=len(nodes), edges=len(edges)).info("graph_retrieve.done")
    return nodes, edges
