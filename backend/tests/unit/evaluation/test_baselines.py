"""Tests for evaluation baselines module."""

from tests.evaluation.baselines import (
    BASELINE_CONFIGS,
    BaselineConfig,
    build_pipeline_kwargs,
    get_baseline_configs,
)


class TestBaselineConfig:
    """Test BaselineConfig."""

    def test_all_configs_exist(self):
        assert "llm_only" in BASELINE_CONFIGS
        assert "plain_rag" in BASELINE_CONFIGS
        assert "graph_only" in BASELINE_CONFIGS
        assert "hybrid_full" in BASELINE_CONFIGS

    def test_llm_only_no_retrieval(self):
        c = BASELINE_CONFIGS["llm_only"]
        assert not c.use_vector_search
        assert not c.use_graph_retrieval
        assert not c.use_classification
        assert not c.use_provenance

    def test_plain_rag_vector_only(self):
        c = BASELINE_CONFIGS["plain_rag"]
        assert c.use_vector_search
        assert not c.use_graph_retrieval

    def test_graph_only_no_vector(self):
        c = BASELINE_CONFIGS["graph_only"]
        assert not c.use_vector_search
        assert c.use_graph_retrieval

    def test_hybrid_full_all_enabled(self):
        c = BASELINE_CONFIGS["hybrid_full"]
        assert c.use_vector_search
        assert c.use_graph_retrieval
        assert c.use_classification
        assert c.use_provenance

    def test_get_baseline_configs_returns_copy(self):
        configs = get_baseline_configs()
        assert len(configs) == 4
        configs["new"] = BaselineConfig(name="new", description="new")
        assert "new" not in BASELINE_CONFIGS


class TestBuildPipelineKwargs:
    """Test build_pipeline_kwargs."""

    def _dummy_fn(self):
        return lambda: None

    def test_basic_kwargs(self):
        config = BASELINE_CONFIGS["plain_rag"]
        fn = self._dummy_fn()
        kwargs = build_pipeline_kwargs(
            config=config,
            embed_fn=fn, search_fn=fn, traverse_fn=fn,
            build_context_fn=fn, generate_fn=fn,
        )
        assert "embed_fn" in kwargs
        assert "search_fn" in kwargs
        assert "traverse_fn" in kwargs
        assert kwargs["top_k"] == 5

    def test_hybrid_includes_graph_retrieve(self):
        config = BASELINE_CONFIGS["hybrid_full"]
        fn = self._dummy_fn()
        kwargs = build_pipeline_kwargs(
            config=config,
            embed_fn=fn, search_fn=fn, traverse_fn=fn,
            build_context_fn=fn, generate_fn=fn,
            classify_fn=fn, route_fn=fn,
            graph_retrieve_fn=fn, merge_fn=fn,
            provenance_fn=fn,
        )
        assert "classify_fn" in kwargs
        assert "graph_retrieve_fn" in kwargs
        assert kwargs["enable_provenance"] is True

    def test_llm_only_no_extras(self):
        config = BASELINE_CONFIGS["llm_only"]
        fn = self._dummy_fn()
        kwargs = build_pipeline_kwargs(
            config=config,
            embed_fn=fn, search_fn=fn, traverse_fn=fn,
            build_context_fn=fn, generate_fn=fn,
        )
        assert "classify_fn" not in kwargs
        assert "graph_retrieve_fn" not in kwargs
        assert kwargs["enable_provenance"] is False
