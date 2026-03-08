"""Community detection via Leiden algorithm on co-authorship graph.

Uses NetworkX + cdlib for pure Python community detection.
No Neo4j GDS plugin required.
"""

from collections import defaultdict

import networkx as nx
from cdlib import algorithms


def build_coauthorship_graph(
    authored_edges: list[dict],
) -> nx.Graph:
    """Build a co-authorship graph from AUTHORED relationships.

    Two authors are connected if they co-authored at least one paper.
    Edge weight = number of co-authored papers.

    Args:
        authored_edges: List of dicts with 'author_uid' and 'paper_uid' keys.

    Returns:
        Undirected NetworkX graph where nodes are author UIDs
        and edges have 'weight' = co-authorship count.
    """
    # Group authors by paper
    paper_authors: dict[str, list[str]] = defaultdict(list)
    for edge in authored_edges:
        paper_authors[edge["paper_uid"]].append(edge["author_uid"])

    # Build co-authorship edges
    G = nx.Graph()
    coauthor_counts: dict[tuple[str, str], int] = defaultdict(int)

    for paper_uid, authors in paper_authors.items():
        for i, a in enumerate(authors):
            G.add_node(a)
            for b in authors[i + 1 :]:
                pair = (min(a, b), max(a, b))
                coauthor_counts[pair] += 1

    for (a, b), weight in coauthor_counts.items():
        G.add_edge(a, b, weight=weight)

    return G


def detect_communities(
    graph: nx.Graph,
) -> dict[str, int]:
    """Run Leiden community detection on a co-authorship graph.

    Args:
        graph: Undirected NetworkX graph (from build_coauthorship_graph).

    Returns:
        Dict mapping node_id → community_id (0-based).
        Isolated nodes get their own community.
    """
    if graph.number_of_nodes() == 0:
        return {}

    # For very small graphs or disconnected nodes, handle gracefully
    if graph.number_of_edges() == 0:
        return {node: i for i, node in enumerate(graph.nodes())}

    # cdlib/igraph requires integer node IDs; remap string → int
    nodes = list(graph.nodes())
    node_to_int = {n: i for i, n in enumerate(nodes)}
    int_to_node = {i: n for i, n in enumerate(nodes)}

    int_graph = nx.Graph()
    int_graph.add_nodes_from(range(len(nodes)))
    for u, v, data in graph.edges(data=True):
        int_graph.add_edge(node_to_int[u], node_to_int[v], **data)

    # Run Leiden via cdlib
    communities = algorithms.leiden(int_graph)

    # Map each node back to original ID with community
    node_to_community: dict[str, int] = {}
    for community_id, members in enumerate(communities.communities):
        for int_node in members:
            node_to_community[int_to_node[int_node]] = community_id

    return node_to_community
