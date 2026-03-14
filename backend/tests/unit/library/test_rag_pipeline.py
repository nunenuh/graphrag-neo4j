"""Unit tests for library.graph.rag_pipeline."""

from graphrag_service.library.graph.rag_pipeline import build_rag_graph, run_rag_pipeline


class _FakeResult:
    """Minimal search result object for testing."""

    def __init__(self, id, label, name, score):
        self.id = id
        self.label = label
        self.name = name
        self.score = score
        self.properties = {}


class TestBuildRagGraph:
    def test_returns_state_graph(self):
        graph = build_rag_graph(
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, [], []),
            build_context_fn=lambda s, e, n=None:"ctx",
            generate_fn=lambda q, c: "answer",
        )
        assert graph is not None


class TestRunRagPipeline:
    def test_full_pipeline_linear(self):
        """Test pipeline without classify/route (linear VECTOR_ONLY)."""
        search_results = [_FakeResult("m1", "Method", "ResNet", 0.9)]

        result = run_rag_pipeline(
            question="What is ResNet?",
            embed_fn=lambda q: [0.1, 0.2],
            search_fn=lambda v, k: search_results,
            traverse_fn=lambda ids: ({"m1": {"uid": "m1", "name": "ResNet"}}, [], []),
            build_context_fn=lambda s, e, n=None:"ResNet is a deep network.",
            generate_fn=lambda q, c: f"Based on context: {c}",
        )
        assert "ResNet" in result["answer"]
        assert result["question"] == "What is ResNet?"
        assert len(result["seed_nodes"]) == 1
        assert "subgraph" in result
        assert result["query_type"] == "EXPLORATORY"
        assert result["retrieval_strategy"] == "VECTOR_ONLY"

    def test_empty_search_results(self):
        result = run_rag_pipeline(
            question="Unknown topic",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, [], []),
            build_context_fn=lambda s, e, n=None:"",
            generate_fn=lambda q, c: "I don't know.",
        )
        assert result["answer"] == "I don't know."
        assert result["seed_nodes"] == []

    def test_with_classification(self):
        """Test pipeline with classify_fn and route_fn (agentic mode)."""
        search_results = [_FakeResult("m1", "Method", "ResNet", 0.9)]

        result = run_rag_pipeline(
            question="What is ResNet?",
            embed_fn=lambda q: [0.1, 0.2],
            search_fn=lambda v, k: search_results,
            traverse_fn=lambda ids: ({"m1": {"uid": "m1", "name": "ResNet"}}, [], []),
            build_context_fn=lambda s, e, n=None:"ResNet context",
            generate_fn=lambda q, c: "ResNet answer",
            classify_fn=lambda q: {
                "query_type": "FACTUAL_LOOKUP",
                "confidence": 0.95,
                "entities": ["ResNet"],
            },
            route_fn=lambda qt: "GRAPH_ONLY",
            graph_retrieve_fn=lambda qt, ents: (
                {"m1": {"uid": "m1", "name": "ResNet"}},
                [{"from_id": "m1", "to_id": "p1", "type": "USES"}],
            ),
        )
        assert result["query_type"] == "FACTUAL_LOOKUP"
        assert result["retrieval_strategy"] == "GRAPH_ONLY"
        assert "ResNet" in result["answer"]

    def test_with_provenance(self):
        result = run_rag_pipeline(
            question="What is YOLO?",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, [], []),
            build_context_fn=lambda s, e, n=None:"context",
            generate_fn=lambda q, c: "YOLO is a detection method.",
            provenance_fn=lambda answer, ctx: {
                "provenance_score": 0.85,
                "unsupported_claims": [],
            },
            enable_provenance=True,
        )
        assert result["provenance_score"] == 0.85
        assert result["unsupported_claims"] == []

    def test_provenance_disabled(self):
        result = run_rag_pipeline(
            question="test",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, [], []),
            build_context_fn=lambda s, e, n=None:"",
            generate_fn=lambda q, c: "answer",
            enable_provenance=False,
        )
        assert result["provenance_score"] == 1.0
        assert result["unsupported_claims"] == []

    def test_hybrid_parallel(self):
        search_results = [_FakeResult("v1", "Method", "VecResult", 0.8)]

        result = run_rag_pipeline(
            question="Compare BERT vs GPT",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: search_results,
            traverse_fn=lambda ids: (
                {"v1": {"uid": "v1", "name": "VecResult"}},
                [{"from_id": "v1", "to_id": "v2", "type": "REL"}],
                [],
            ),
            build_context_fn=lambda s, e, n=None:"merged context",
            generate_fn=lambda q, c: "comparison answer",
            classify_fn=lambda q: {
                "query_type": "COMPARISON",
                "confidence": 0.9,
                "entities": ["BERT", "GPT"],
            },
            route_fn=lambda qt: "HYBRID_PARALLEL",
            graph_retrieve_fn=lambda qt, ents: (
                {"g1": {"uid": "g1", "name": "GraphResult"}},
                [{"from_id": "g1", "to_id": "g2", "type": "REL2"}],
            ),
            merge_fn=lambda gn, ge, vn, ve: ({**gn, **vn}, ge + ve),
        )
        assert result["retrieval_strategy"] == "HYBRID_PARALLEL"
        assert "comparison answer" in result["answer"]

    def test_step_timings_present(self):
        result = run_rag_pipeline(
            question="test",
            embed_fn=lambda q: [0.1],
            search_fn=lambda v, k: [],
            traverse_fn=lambda ids: ({}, [], []),
            build_context_fn=lambda s, e, n=None:"",
            generate_fn=lambda q, c: "answer",
        )
        timings = result["step_timings"]
        assert "analyze" in timings
        assert "embed" in timings
        assert "retrieve" in timings
        assert "build_context" in timings
        assert "generate" in timings
        assert "validate" in timings
