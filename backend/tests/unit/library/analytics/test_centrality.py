"""Unit tests for library/analytics/centrality.py."""

import networkx as nx

from graphrag_service.library.analytics.centrality import (
    compute_centrality,
    compute_h_index,
    compute_h_index_from_edges,
)


class TestComputeCentrality:
    def test_empty_graph(self):
        G = nx.Graph()
        assert compute_centrality(G) == {}

    def test_simple_graph(self):
        G = nx.Graph()
        G.add_edge("a", "b", weight=1)
        G.add_edge("b", "c", weight=1)
        result = compute_centrality(G)
        assert len(result) == 3
        # b should have highest betweenness (it's the bridge)
        assert result["b"]["betweenness"] > result["a"]["betweenness"]
        assert result["b"]["betweenness"] > result["c"]["betweenness"]

    def test_star_graph(self):
        G = nx.star_graph(4)  # center=0, leaves=1,2,3,4
        # Convert to string nodes
        mapping = {i: f"n{i}" for i in range(5)}
        G = nx.relabel_nodes(G, mapping)
        for u, v in G.edges():
            G[u][v]["weight"] = 1
        result = compute_centrality(G)
        # Center should have highest PageRank
        assert result["n0"]["pagerank"] > result["n1"]["pagerank"]

    def test_returns_correct_keys(self):
        G = nx.Graph()
        G.add_edge("a", "b", weight=1)
        result = compute_centrality(G)
        assert "pagerank" in result["a"]
        assert "betweenness" in result["a"]


class TestComputeHIndex:
    def test_basic(self):
        # Author with 3 papers, each cited once → h=1
        result = compute_h_index({"a1": [1, 1, 1]})
        assert result["a1"] == 1

    def test_high_h_index(self):
        # 5 papers with 5+ citations each → h=5
        result = compute_h_index({"a1": [10, 8, 6, 5, 5, 2, 1]})
        assert result["a1"] == 5

    def test_zero(self):
        result = compute_h_index({"a1": [0, 0, 0]})
        assert result["a1"] == 0

    def test_empty(self):
        assert compute_h_index({}) == {}

    def test_single_paper(self):
        result = compute_h_index({"a1": [5]})
        assert result["a1"] == 1


class TestComputeHIndexFromEdges:
    def test_basic(self):
        edges = [
            {"author_uid": "a1", "paper_uid": "p1"},
            {"author_uid": "a1", "paper_uid": "p2"},
            {"author_uid": "a1", "paper_uid": "p3"},
            {"author_uid": "a2", "paper_uid": "p1"},
        ]
        result = compute_h_index_from_edges(edges)
        # a1 has 3 papers → h=3 (each counts as 1 citation)
        assert result["a1"] == 3
        assert result["a2"] == 1

    def test_empty(self):
        assert compute_h_index_from_edges([]) == {}
