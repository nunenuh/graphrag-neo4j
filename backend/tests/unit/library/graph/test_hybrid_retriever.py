"""Unit tests for library/graph/hybrid_retriever.py."""

from graphrag_service.library.graph.hybrid_retriever import (
    merge_nodes_rrf,
    merge_rrf,
    rrf_score,
)


class TestRRFScore:
    def test_rank_zero(self):
        assert rrf_score(0, k=60) == 1.0 / 60

    def test_rank_one(self):
        assert rrf_score(1, k=60) == 1.0 / 61

    def test_custom_k(self):
        assert rrf_score(0, k=10) == 1.0 / 10

    def test_higher_rank_lower_score(self):
        assert rrf_score(0) > rrf_score(1) > rrf_score(10)


class TestMergeRRF:
    def test_disjoint_lists(self):
        list_a = [{"uid": "a1"}, {"uid": "a2"}]
        list_b = [{"uid": "b1"}, {"uid": "b2"}]
        result = merge_rrf(list_a, list_b)
        uids = [r["uid"] for r in result]
        assert set(uids) == {"a1", "a2", "b1", "b2"}
        assert len(result) == 4
        # All should have rrf_score
        for item in result:
            assert "rrf_score" in item

    def test_overlapping_items_boosted(self):
        list_a = [{"uid": "x1"}, {"uid": "x2"}]
        list_b = [{"uid": "x1"}, {"uid": "x3"}]
        result = merge_rrf(list_a, list_b)
        # x1 appears in both → should have highest score
        assert result[0]["uid"] == "x1"

    def test_empty_lists(self):
        assert merge_rrf([], []) == []

    def test_one_empty(self):
        list_a = [{"uid": "a1"}]
        result = merge_rrf(list_a, [])
        assert len(result) == 1
        assert result[0]["uid"] == "a1"

    def test_preserves_original_data(self):
        list_a = [{"uid": "a1", "name": "ResNet", "label": "Method"}]
        result = merge_rrf(list_a, [])
        assert result[0]["name"] == "ResNet"
        assert result[0]["label"] == "Method"

    def test_missing_uid_skipped(self):
        list_a = [{"uid": "a1"}, {"name": "no_uid"}]
        result = merge_rrf(list_a, [])
        assert len(result) == 1


class TestMergeNodesRRF:
    def test_basic_merge(self):
        graph_nodes = {"g1": {"uid": "g1", "name": "A"}}
        graph_edges = [{"from_id": "g1", "to_id": "g2", "type": "REL"}]
        vector_nodes = {"v1": {"uid": "v1", "name": "B"}}
        vector_edges = [{"from_id": "v1", "to_id": "v2", "type": "REL2"}]

        nodes, edges = merge_nodes_rrf(
            graph_nodes, graph_edges, vector_nodes, vector_edges
        )
        assert "g1" in nodes or "v1" in nodes
        assert len(edges) == 2

    def test_deduplicates_edges(self):
        edge = {"from_id": "a", "to_id": "b", "type": "REL"}
        _, edges = merge_nodes_rrf({}, [edge], {}, [edge])
        assert len(edges) == 1

    def test_empty(self):
        nodes, edges = merge_nodes_rrf({}, [], {}, [])
        assert nodes == {}
        assert edges == []

    def test_overlapping_nodes(self):
        shared = {"uid": "s1", "name": "Shared"}
        nodes, _ = merge_nodes_rrf(
            {"s1": shared}, [], {"s1": shared}, []
        )
        assert "s1" in nodes
