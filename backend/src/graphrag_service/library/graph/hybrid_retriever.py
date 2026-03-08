"""Hybrid retrieval with Reciprocal Rank Fusion (RRF) merge.

Supports parallel and sequential hybrid strategies.
"""

from loguru import logger


def rrf_score(rank: int, k: int = 60) -> float:
    """Compute RRF score for a given rank.

    Args:
        rank: 0-based rank position.
        k: Smoothing constant (default 60).

    Returns:
        RRF score as float.
    """
    return 1.0 / (k + rank)


def merge_rrf(
    list_a: list[dict],
    list_b: list[dict],
    k: int = 60,
    id_key: str = "uid",
) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion.

    Args:
        list_a: First ranked result list (dicts with id_key).
        list_b: Second ranked result list (dicts with id_key).
        k: RRF smoothing constant.
        id_key: Key to use as unique identifier.

    Returns:
        Merged list sorted by combined RRF score (descending).
    """
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for rank, item in enumerate(list_a):
        uid = item.get(id_key, "")
        if not uid:
            continue
        scores[uid] = scores.get(uid, 0.0) + rrf_score(rank, k)
        items[uid] = item

    for rank, item in enumerate(list_b):
        uid = item.get(id_key, "")
        if not uid:
            continue
        scores[uid] = scores.get(uid, 0.0) + rrf_score(rank, k)
        if uid not in items:
            items[uid] = item

    sorted_ids = sorted(scores.keys(), key=lambda uid: scores[uid], reverse=True)
    result = []
    for uid in sorted_ids:
        item = dict(items[uid])
        item["rrf_score"] = round(scores[uid], 6)
        result.append(item)

    return result


def merge_nodes_rrf(
    graph_nodes: dict[str, dict],
    graph_edges: list[dict],
    vector_nodes: dict[str, dict],
    vector_edges: list[dict],
    k: int = 60,
) -> tuple[dict[str, dict], list[dict]]:
    """Merge graph and vector retrieval results using RRF on nodes.

    Args:
        graph_nodes: Nodes from graph-only retrieval (uid → dict).
        graph_edges: Edges from graph-only retrieval.
        vector_nodes: Nodes from vector retrieval (uid → dict).
        vector_edges: Edges from vector retrieval.
        k: RRF smoothing constant.

    Returns:
        Merged (nodes_by_id, edges_list).
    """
    # Rank nodes by appearance order in each source
    graph_list = list(graph_nodes.values())
    vector_list = list(vector_nodes.values())

    merged = merge_rrf(graph_list, vector_list, k=k)

    merged_nodes: dict[str, dict] = {}
    for item in merged:
        uid = item.get("uid", "")
        if uid:
            merged_nodes[uid] = item

    # Combine edges, deduplicate by (from_id, to_id, type)
    seen_edges: set[tuple[str, str, str]] = set()
    merged_edges: list[dict] = []
    for e in graph_edges + vector_edges:
        key = (e.get("from_id", ""), e.get("to_id", ""), e.get("type", ""))
        if key not in seen_edges:
            seen_edges.add(key)
            merged_edges.append(e)

    logger.bind(
        graph_nodes=len(graph_nodes),
        vector_nodes=len(vector_nodes),
        merged_nodes=len(merged_nodes),
        merged_edges=len(merged_edges),
    ).info("merge_rrf.done")

    return merged_nodes, merged_edges
