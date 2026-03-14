"""Unit tests for library.generator (context building)."""

from graphrag_service.library.generator import build_context


class TestBuildContext:
    def test_basic_output(self):
        seeds = [{"label": "Paper", "name": "ResNet", "score": 0.95}]
        edges = [{"from_id": "p1", "to_id": "d1", "type": "EVALUATED_ON"}]
        result = build_context(seeds, edges)
        assert "GRAPH CONTEXT" in result
        assert "ResNet" in result
        assert "EVALUATED_ON" in result

    def test_empty_inputs(self):
        result = build_context([], [])
        assert "SEED NODES" in result
        assert "RELATIONSHIPS" in result

    def test_limits_edges_per_type(self):
        seeds = []
        edges = [{"from_id": f"a{i}", "to_id": f"b{i}", "type": "REL"} for i in range(50)]
        result = build_context(seeds, edges)
        # Should show max 15 per type, plus summary of remaining
        assert "and 35 more" in result

    def test_score_formatting(self):
        seeds = [{"label": "Method", "name": "BERT", "score": 0.12345}]
        result = build_context(seeds, [])
        assert "score=0.12" in result

    def test_resolves_uids_to_names(self):
        edges = [{"from_id": "a1", "to_id": "p1", "type": "AUTHORED"}]
        nodes = [
            {"uid": "a1", "label": "Author", "name": "Alice"},
            {"uid": "p1", "label": "Paper", "title": "My Paper"},
        ]
        result = build_context([], edges, nodes)
        assert "[Author] Alice" in result
        assert "[Paper] My Paper" in result

    def test_edge_without_nodes_shows_uid(self):
        edges = [{"from_id": "a", "to_id": "b", "type": "REL"}]
        result = build_context([], edges)
        assert "a -> b" in result

    def test_priority_edge_ordering(self):
        edges = [
            {"from_id": "x", "to_id": "y", "type": "USES_METHOD"},
            {"from_id": "a", "to_id": "p", "type": "AUTHORED"},
        ]
        result = build_context([], edges)
        # AUTHORED should appear before USES_METHOD
        authored_pos = result.index("AUTHORED")
        uses_pos = result.index("USES_METHOD")
        assert authored_pos < uses_pos

    def test_groups_edges_by_type(self):
        edges = [
            {"from_id": "a1", "to_id": "p1", "type": "AUTHORED"},
            {"from_id": "a2", "to_id": "p2", "type": "AUTHORED"},
            {"from_id": "p1", "to_id": "t1", "type": "ADDRESSES"},
        ]
        result = build_context([], edges)
        assert "AUTHORED (2 total)" in result
        assert "ADDRESSES (1 total)" in result
