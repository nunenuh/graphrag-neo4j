"""Centrality metrics for author co-authorship graph.

Computes PageRank, betweenness centrality, and h-index.
"""

from collections import defaultdict

import networkx as nx


def compute_centrality(
    graph: nx.Graph,
    betweenness_sample: int = 500,
) -> dict[str, dict[str, float]]:
    """Compute PageRank and approximate betweenness centrality.

    Uses sampled betweenness (k=500 random pivots) instead of exact
    computation, which is O(V*E) and infeasible for large graphs.

    Args:
        graph: Undirected NetworkX co-authorship graph.
        betweenness_sample: Number of random pivot nodes for approximation.

    Returns:
        Dict mapping node_id → {'pagerank': float, 'betweenness': float}.
    """
    if graph.number_of_nodes() == 0:
        return {}

    from loguru import logger

    logger.info(f"Computing PageRank on {graph.number_of_nodes():,} nodes...")
    pagerank = nx.pagerank(graph, weight="weight")

    n_nodes = graph.number_of_nodes()
    if n_nodes > 10_000:
        k = min(betweenness_sample, n_nodes)
        logger.info(f"Computing approximate betweenness (k={k}) on {n_nodes:,} nodes...")
        betweenness = nx.betweenness_centrality(graph, weight="weight", k=k)
    else:
        logger.info(f"Computing exact betweenness on {n_nodes:,} nodes...")
        betweenness = nx.betweenness_centrality(graph, weight="weight")

    result: dict[str, dict[str, float]] = {}
    for node in graph.nodes():
        result[node] = {
            "pagerank": round(pagerank.get(node, 0.0), 8),
            "betweenness": round(betweenness.get(node, 0.0), 8),
        }
    return result


def compute_h_index(
    author_paper_counts: dict[str, list[int]],
) -> dict[str, int]:
    """Compute h-index for each author.

    Args:
        author_paper_counts: Dict mapping author_uid → list of citation counts
            (or paper counts per year as proxy). For simplicity, we use the
            number of papers an author has as h-index proxy when citation
            data isn't available.

    Returns:
        Dict mapping author_uid → h_index.
    """
    result: dict[str, int] = {}
    for author_uid, counts in author_paper_counts.items():
        sorted_counts = sorted(counts, reverse=True)
        h = 0
        for i, c in enumerate(sorted_counts):
            if c >= i + 1:
                h = i + 1
            else:
                break
        result[author_uid] = h
    return result


def compute_h_index_from_edges(
    authored_edges: list[dict],
) -> dict[str, int]:
    """Compute h-index from authored edges (paper count proxy).

    Since we don't have citation data, h-index is based on paper count:
    an author with N papers has h-index = N (each paper counts as 1).

    Args:
        authored_edges: List of dicts with 'author_uid' and 'paper_uid'.

    Returns:
        Dict mapping author_uid → h_index (= paper count for now).
    """
    paper_counts: dict[str, int] = defaultdict(int)
    for edge in authored_edges:
        paper_counts[edge["author_uid"]] += 1

    # With no citation data, h-index = paper count as proxy
    return {uid: count for uid, count in paper_counts.items()}
