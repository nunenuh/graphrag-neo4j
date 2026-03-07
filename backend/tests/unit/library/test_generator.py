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

    def test_limits_edges_to_30(self):
        seeds = []
        edges = [{"from_id": f"a{i}", "to_id": f"b{i}", "type": "REL"} for i in range(50)]
        result = build_context(seeds, edges)
        # Should only show 30 relationships
        assert result.count("-[REL]->") == 30

    def test_score_formatting(self):
        seeds = [{"label": "Method", "name": "BERT", "score": 0.12345}]
        result = build_context(seeds, [])
        assert "score=0.12" in result

    def test_edge_properties(self):
        edges = [{"from_id": "a", "to_id": "b", "type": "REL", "properties": {"k": "v"}}]
        result = build_context([], edges)
        assert "{'k': 'v'}" in result

    def test_edge_without_properties(self):
        edges = [{"from_id": "a", "to_id": "b", "type": "REL"}]
        result = build_context([], edges)
        assert "(a) -[REL]-> (b)" in result
