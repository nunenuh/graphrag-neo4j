"""BM25 fulltext search via Neo4j fulltext indexes.

Uses Neo4j's built-in fulltext indexes (backed by Lucene) for keyword search
across all searchable node types.
"""

from loguru import logger


# Fulltext index definitions: (index_name, label, properties)
FULLTEXT_INDEXES = [
    ("fulltext_paper", "Paper", ["title", "abstract"]),
    ("fulltext_method", "Method", ["name", "full_name", "description"]),
    ("fulltext_task", "Task", ["name", "description"]),
    ("fulltext_dataset", "Dataset", ["name", "description"]),
]


def create_fulltext_indexes(run_cypher_fn: callable) -> int:
    """Create fulltext indexes for all searchable node types.

    Args:
        run_cypher_fn: Callable to execute Cypher (client.run_query).

    Returns:
        Number of indexes created.
    """
    created = 0
    for index_name, label, properties in FULLTEXT_INDEXES:
        props = ", ".join(f"n.{p}" for p in properties)
        cypher = (
            f"CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS "
            f"FOR (n:{label}) ON EACH [{props}]"
        )
        try:
            run_cypher_fn(cypher)
            logger.info(f"Fulltext index created: {index_name} on {label}({', '.join(properties)})")
            created += 1
        except Exception as e:
            logger.bind(index=index_name, error=str(e)).warning("fulltext_index.create_failed")
    return created


def bm25_search(
    query: str,
    run_cypher_fn: callable,
    top_k: int = 10,
) -> list[dict]:
    """Search across all fulltext indexes and return top-k results.

    Args:
        query: Natural language search query.
        run_cypher_fn: Callable to execute Cypher.
        top_k: Max results to return.

    Returns:
        List of dicts with keys: uid, label, name, score, properties.
    """
    if not query.strip():
        return []

    # Escape special Lucene characters
    escaped = _escape_lucene(query)

    all_results: list[dict] = []
    for index_name, label, _props in FULLTEXT_INDEXES:
        cypher = (
            "CALL db.index.fulltext.queryNodes($index, $query) "
            "YIELD node, score "
            "RETURN node, score, labels(node)[0] AS label "
            "LIMIT $limit"
        )
        try:
            rows = run_cypher_fn(cypher, {
                "index": index_name,
                "query": escaped,
                "limit": top_k,
            })
            for row in rows:
                node = row["node"]
                props = {k: v for k, v in dict(node).items() if k != "embedding"}
                all_results.append({
                    "uid": props.get("uid", ""),
                    "label": row["label"],
                    "name": props.get("name") or props.get("title", ""),
                    "score": row["score"],
                    "properties": props,
                })
        except Exception as e:
            logger.bind(index=index_name, error=str(e)).debug("bm25_search.index_failed")

    # Sort by score descending, return top-k
    all_results.sort(key=lambda r: r["score"], reverse=True)
    logger.bind(total_results=len(all_results), top_k=top_k).info("bm25_search.done")
    return all_results[:top_k]


def _escape_lucene(query: str) -> str:
    """Escape special Lucene query characters."""
    special = r'+-&|!(){}[]^"~*?:\/'
    escaped = []
    for ch in query:
        if ch in special:
            escaped.append(f"\\{ch}")
        else:
            escaped.append(ch)
    return "".join(escaped)
