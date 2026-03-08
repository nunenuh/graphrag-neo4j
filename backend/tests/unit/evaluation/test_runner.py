"""Tests for evaluation runner module."""

from tests.evaluation.metrics import EvalResult
from tests.evaluation.queries import EvalQuery
from tests.evaluation.runner import EvaluationRunner


def _make_pipeline_fn(answer: str = "test answer", fail: bool = False):
    """Create a mock pipeline function."""
    def fn(question: str) -> dict:
        if fail:
            raise RuntimeError("pipeline error")
        return {
            "answer": answer,
            "seed_nodes": [{"name": "TestNode"}],
            "subgraph": {"nodes": [{"name": "TestNode"}], "edges": []},
            "query_type": "FACTUAL_LOOKUP",
            "retrieval_strategy": "VECTOR_ONLY",
            "provenance_score": 0.85,
            "unsupported_claims": [],
        }
    return fn


def _make_query(qid: str = "t1") -> EvalQuery:
    return EvalQuery(
        id=qid,
        category="FACTUAL_LOOKUP",
        question="What is X?",
        expected_entities=["TestNode"],
        gold_answer_keywords=["test"],
    )


class TestEvaluationRunner:
    """Test EvaluationRunner."""

    def test_run_single_success(self):
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(),
            queries=[_make_query()],
        )
        result = runner.run_single(_make_query())
        assert result.query_id == "t1"
        assert result.answer == "test answer"
        assert result.latency_ms >= 0
        assert "entity_f1" in result.metrics

    def test_run_single_failure(self):
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(fail=True),
            queries=[_make_query()],
        )
        result = runner.run_single(_make_query())
        assert "ERROR" in result.answer
        assert result.metrics.get("error") == 1.0

    def test_run_all_produces_report(self):
        queries = [_make_query("q1"), _make_query("q2")]
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(),
            queries=queries,
        )
        report = runner.run_all(system_name="test_system")
        assert report.system_name == "test_system"
        assert report.total_queries == 2
        assert report.successful_queries == 2
        assert len(report.results) == 2
        assert len(report.failures) == 0

    def test_run_all_with_failures(self):
        queries = [_make_query("q1")]
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(fail=True),
            queries=queries,
        )
        report = runner.run_all()
        assert report.successful_queries == 0
        assert "q1" in report.failures

    def test_run_all_metrics_summary(self):
        queries = [_make_query("q1"), _make_query("q2")]
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(),
            queries=queries,
        )
        report = runner.run_all()
        assert report.metrics_summary  # not empty
        assert "entity_f1" in report.metrics_summary

    def test_run_all_category_breakdown(self):
        queries = [_make_query("q1")]
        runner = EvaluationRunner(
            pipeline_fn=_make_pipeline_fn(),
            queries=queries,
        )
        report = runner.run_all()
        assert "FACTUAL_LOOKUP" in report.metrics_by_category
