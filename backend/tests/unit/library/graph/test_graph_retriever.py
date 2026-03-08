"""Unit tests for library/graph/graph_retriever.py."""

from graphrag_service.library.graph.graph_retriever import (
    _build_pattern,
    graph_retrieve,
)


class TestBuildPattern:
    def test_empty_entities(self):
        assert _build_pattern([]) == ".*"

    def test_single_entity(self):
        pattern = _build_pattern(["ResNet"])
        assert "ResNet" in pattern
        assert "(?i)" in pattern

    def test_multiple_entities(self):
        pattern = _build_pattern(["BERT", "GPT"])
        assert "BERT" in pattern
        assert "GPT" in pattern
        assert "|" in pattern

    def test_escapes_parens(self):
        pattern = _build_pattern(["YOLOv3 (tiny)"])
        assert "\\(" in pattern
        assert "\\)" in pattern


class TestGraphRetrieve:
    def test_basic_retrieval(self):
        def mock_cypher(query, params):
            return [
                {
                    "n": {"uid": "m1", "name": "ResNet", "embedding": [0.1]},
                    "label": "Method",
                    "edges": [
                        {"from": "m1", "to": "p1", "type": "USES", "props": {}},
                    ],
                    "neighbors": [
                        {"node": {"uid": "p1", "name": "Paper1"}, "label": "Paper"},
                    ],
                }
            ]

        nodes, edges = graph_retrieve("FACTUAL_LOOKUP", ["ResNet"], mock_cypher)
        assert "m1" in nodes
        assert nodes["m1"]["name"] == "ResNet"
        assert "embedding" not in nodes["m1"]
        assert len(edges) == 1

    def test_empty_results(self):
        nodes, edges = graph_retrieve("FACTUAL_LOOKUP", ["Unknown"], lambda q, p: [])
        assert nodes == {}
        assert edges == []

    def test_cypher_exception(self):
        def failing_cypher(query, params):
            raise RuntimeError("Neo4j down")

        nodes, edges = graph_retrieve("FACTUAL_LOOKUP", ["ResNet"], failing_cypher)
        assert nodes == {}
        assert edges == []

    def test_network_query_type(self):
        def mock_cypher(query, params):
            return [
                {
                    "a": {"uid": "a1", "name": "Hinton"},
                    "a_label": "Author",
                    "p": {"uid": "p1", "name": "Paper1"},
                    "p_label": "Paper",
                    "coauthors": [
                        {"uid": "a2", "name": "LeCun"},
                    ],
                    "edges": [],
                    "neighbors": [],
                }
            ]

        nodes, edges = graph_retrieve("NETWORK", ["Hinton"], mock_cypher)
        assert "a1" in nodes
        assert "a2" in nodes
        assert nodes["a2"]["label"] == "Author"

    def test_unknown_query_type_uses_fallback(self):
        called_with = {}

        def mock_cypher(query, params):
            called_with["query"] = query
            return []

        graph_retrieve("UNKNOWN_TYPE", ["test"], mock_cypher)
        # Should still execute (using fallback template)
        assert "query" in called_with
