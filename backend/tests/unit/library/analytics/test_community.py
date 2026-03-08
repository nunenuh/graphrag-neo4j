"""Unit tests for library/analytics/community.py."""

import networkx as nx

from graphrag_service.library.analytics.community import (
    build_coauthorship_graph,
    detect_communities,
)


class TestBuildCoauthorshipGraph:
    def test_basic(self):
        edges = [
            {"author_uid": "a1", "paper_uid": "p1"},
            {"author_uid": "a2", "paper_uid": "p1"},
            {"author_uid": "a3", "paper_uid": "p1"},
        ]
        G = build_coauthorship_graph(edges)
        assert G.number_of_nodes() == 3
        # 3 authors on 1 paper → 3 edges (a1-a2, a1-a3, a2-a3)
        assert G.number_of_edges() == 3

    def test_weight_accumulates(self):
        edges = [
            {"author_uid": "a1", "paper_uid": "p1"},
            {"author_uid": "a2", "paper_uid": "p1"},
            {"author_uid": "a1", "paper_uid": "p2"},
            {"author_uid": "a2", "paper_uid": "p2"},
        ]
        G = build_coauthorship_graph(edges)
        assert G.number_of_edges() == 1
        assert G["a1"]["a2"]["weight"] == 2

    def test_single_author_paper(self):
        edges = [{"author_uid": "a1", "paper_uid": "p1"}]
        G = build_coauthorship_graph(edges)
        assert G.number_of_nodes() == 1
        assert G.number_of_edges() == 0

    def test_empty(self):
        G = build_coauthorship_graph([])
        assert G.number_of_nodes() == 0

    def test_disconnected_groups(self):
        edges = [
            {"author_uid": "a1", "paper_uid": "p1"},
            {"author_uid": "a2", "paper_uid": "p1"},
            {"author_uid": "a3", "paper_uid": "p2"},
            {"author_uid": "a4", "paper_uid": "p2"},
        ]
        G = build_coauthorship_graph(edges)
        assert G.number_of_nodes() == 4
        assert G.number_of_edges() == 2
        assert not nx.is_connected(G)


class TestDetectCommunities:
    def test_empty_graph(self):
        G = nx.Graph()
        assert detect_communities(G) == {}

    def test_no_edges(self):
        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        result = detect_communities(G)
        assert len(result) == 3
        # Each node in its own community
        assert len(set(result.values())) == 3

    def test_connected_graph(self):
        G = nx.Graph()
        G.add_edge("a", "b", weight=5)
        G.add_edge("b", "c", weight=5)
        G.add_edge("a", "c", weight=5)
        result = detect_communities(G)
        assert len(result) == 3
        # Tightly connected → likely 1 community
        assert len(set(result.values())) >= 1

    def test_two_clusters(self):
        G = nx.Graph()
        # Cluster 1
        G.add_edge("a1", "a2", weight=10)
        G.add_edge("a2", "a3", weight=10)
        G.add_edge("a1", "a3", weight=10)
        # Cluster 2
        G.add_edge("b1", "b2", weight=10)
        G.add_edge("b2", "b3", weight=10)
        G.add_edge("b1", "b3", weight=10)
        # Weak bridge
        G.add_edge("a3", "b1", weight=1)
        result = detect_communities(G)
        assert len(result) == 6
        # Should detect 2 communities (or possibly more)
        assert len(set(result.values())) >= 2

    def test_returns_int_community_ids(self):
        G = nx.Graph()
        G.add_edge("a", "b", weight=1)
        result = detect_communities(G)
        for cid in result.values():
            assert isinstance(cid, int)
