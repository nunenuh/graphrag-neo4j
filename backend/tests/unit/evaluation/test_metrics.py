"""Tests for evaluation metrics module."""

from tests.evaluation.metrics import (
    EvalResult,
    aggregate_metrics,
    compute_query_metrics,
    entity_extraction_f1,
    keyword_coverage,
    latency_percentile,
    retrieval_precision_at_k,
    retrieval_recall_at_k,
)


class TestEntityExtractionF1:
    """Test entity_extraction_f1."""

    def test_perfect_match(self):
        assert entity_extraction_f1(["A", "B"], ["A", "B"]) == 1.0

    def test_no_match(self):
        assert entity_extraction_f1(["A"], ["B"]) == 0.0

    def test_partial_match(self):
        score = entity_extraction_f1(["A", "B"], ["A", "C"])
        assert 0.0 < score < 1.0

    def test_empty_expected_empty_retrieved(self):
        assert entity_extraction_f1([], []) == 1.0

    def test_empty_expected_with_retrieved(self):
        assert entity_extraction_f1([], ["A"]) == 0.0

    def test_case_insensitive(self):
        assert entity_extraction_f1(["ResNet"], ["resnet"]) == 1.0

    def test_empty_retrieved(self):
        assert entity_extraction_f1(["A"], []) == 0.0


class TestRetrievalPrecisionAtK:
    """Test retrieval_precision_at_k."""

    def test_perfect_precision(self):
        nodes = [{"name": "ResNet"}, {"name": "BERT"}]
        score = retrieval_precision_at_k(["ResNet", "BERT"], nodes, k=2)
        assert score == 1.0

    def test_zero_precision(self):
        nodes = [{"name": "X"}, {"name": "Y"}]
        score = retrieval_precision_at_k(["A"], nodes, k=2)
        assert score == 0.0

    def test_empty_expected(self):
        assert retrieval_precision_at_k([], [{"name": "A"}]) == 1.0

    def test_empty_nodes(self):
        assert retrieval_precision_at_k(["A"], []) == 0.0

    def test_k_limits_results(self):
        nodes = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        score = retrieval_precision_at_k(["A"], nodes, k=1)
        assert score == 1.0


class TestRetrievalRecallAtK:
    """Test retrieval_recall_at_k."""

    def test_perfect_recall(self):
        nodes = [{"name": "A"}, {"name": "B"}]
        score = retrieval_recall_at_k(["A", "B"], nodes, k=10)
        assert score == 1.0

    def test_partial_recall(self):
        nodes = [{"name": "A"}]
        score = retrieval_recall_at_k(["A", "B"], nodes, k=10)
        assert score == 0.5

    def test_empty_expected(self):
        assert retrieval_recall_at_k([], [{"name": "A"}]) == 1.0

    def test_empty_nodes(self):
        assert retrieval_recall_at_k(["A"], []) == 0.0


class TestKeywordCoverage:
    """Test keyword_coverage."""

    def test_full_coverage(self):
        assert keyword_coverage(["attention", "transformer"], "The attention mechanism in transformer models") == 1.0

    def test_no_coverage(self):
        assert keyword_coverage(["xyz"], "The quick brown fox") == 0.0

    def test_partial_coverage(self):
        assert keyword_coverage(["attention", "xyz"], "The attention mechanism") == 0.5

    def test_empty_keywords(self):
        assert keyword_coverage([], "any answer") == 1.0

    def test_case_insensitive(self):
        assert keyword_coverage(["Transformer"], "the TRANSFORMER model") == 1.0


class TestLatencyPercentile:
    """Test latency_percentile."""

    def test_p50(self):
        latencies = [100, 200, 300, 400, 500]
        p50 = latency_percentile(latencies, 50)
        assert p50 == 300.0

    def test_p95(self):
        latencies = list(range(1, 101))
        p95 = latency_percentile(latencies, 95)
        assert p95 == 96.0  # index 95 in 0-indexed sorted list [1..100]

    def test_empty(self):
        assert latency_percentile([], 50) == 0.0

    def test_single_value(self):
        assert latency_percentile([42], 99) == 42.0


class TestComputeQueryMetrics:
    """Test compute_query_metrics."""

    def test_returns_all_metric_keys(self):
        result = EvalResult(
            query_id="t1",
            category="TEST",
            question="test?",
            answer="test answer with attention",
            seed_nodes=[{"name": "Attention"}],
            subgraph={"nodes": [{"name": "Attention"}]},
            latency_ms=100,
            provenance_score=0.8,
        )
        metrics = compute_query_metrics(
            result,
            expected_entities=["Attention"],
            gold_keywords=["attention"],
        )
        assert "entity_f1" in metrics
        assert "precision_at_10" in metrics
        assert "recall_at_10" in metrics
        assert "keyword_coverage" in metrics
        assert "provenance_score" in metrics
        assert "latency_ms" in metrics

    def test_perfect_metrics(self):
        result = EvalResult(
            query_id="t1",
            category="TEST",
            question="test?",
            answer="ResNet uses residual connections",
            seed_nodes=[{"name": "ResNet"}],
            subgraph={"nodes": [{"name": "ResNet"}]},
            latency_ms=50,
            provenance_score=1.0,
        )
        metrics = compute_query_metrics(
            result,
            expected_entities=["ResNet"],
            gold_keywords=["residual"],
        )
        assert metrics["entity_f1"] == 1.0
        assert metrics["keyword_coverage"] == 1.0


class TestAggregateMetrics:
    """Test aggregate_metrics."""

    def test_empty_results(self):
        assert aggregate_metrics([]) == {}

    def test_averages_metrics(self):
        r1 = EvalResult(query_id="t1", category="A", question="q1", answer="a1", latency_ms=100)
        r1.metrics = {"entity_f1": 1.0, "keyword_coverage": 0.5}
        r2 = EvalResult(query_id="t2", category="A", question="q2", answer="a2", latency_ms=200)
        r2.metrics = {"entity_f1": 0.5, "keyword_coverage": 1.0}

        agg = aggregate_metrics([r1, r2])
        assert agg["entity_f1"] == 0.75
        assert agg["keyword_coverage"] == 0.75

    def test_includes_latency_percentiles(self):
        r1 = EvalResult(query_id="t1", category="A", question="q1", answer="a1", latency_ms=100)
        r1.metrics = {"latency_ms": 100.0}
        r2 = EvalResult(query_id="t2", category="A", question="q2", answer="a2", latency_ms=200)
        r2.metrics = {"latency_ms": 200.0}

        agg = aggregate_metrics([r1, r2])
        assert "latency_p50" in agg
        assert "latency_p95" in agg
