"""Unit tests for library.graph.rag_pipeline."""

from graphrag_service.library.graph.rag_pipeline import build_rag_graph, run_rag_pipeline


class TestBuildRagGraph:
    def test_returns_state_graph(self):
        graph = build_rag_graph(
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, []),
            build_context_fn=lambda s, e: "ctx",
            generate_fn=lambda q, c: "answer",
        )
        assert graph is not None


class TestRunRagPipeline:
    def _make_search_result(self, id, label, name, score):
        class R:
            pass
        r = R()
        r.id = id
        r.label = label
        r.name = name
        r.score = score
        r.properties = {}
        return r

    def test_full_pipeline(self):
        search_results = [self._make_search_result("m1", "Method", "ResNet", 0.9)]

        result = run_rag_pipeline(
            question="What is ResNet?",
            embed_fn=lambda q: [0.1, 0.2],
            search_fn=lambda v, k: search_results,
            traverse_fn=lambda ids: ({"m1": {"uid": "m1", "name": "ResNet"}}, []),
            build_context_fn=lambda s, e: "ResNet is a deep network.",
            generate_fn=lambda q, c: f"Based on context: {c}",
        )
        assert "ResNet" in result["answer"]
        assert result["question"] == "What is ResNet?"
        assert len(result["seed_nodes"]) == 1
        assert "subgraph" in result

    def test_empty_search_results(self):
        result = run_rag_pipeline(
            question="Unknown topic",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, []),
            build_context_fn=lambda s, e: "",
            generate_fn=lambda q, c: "I don't know.",
        )
        assert result["answer"] == "I don't know."
        assert result["seed_nodes"] == []
