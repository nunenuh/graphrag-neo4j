"""Tests for evaluation report module."""

import json

from tests.evaluation.metrics import EvalResult
from tests.evaluation.report import EvaluationReport


def _make_report() -> EvaluationReport:
    """Create a sample report for testing."""
    r1 = EvalResult(
        query_id="t1", category="FACTUAL", question="q1",
        answer="answer1", latency_ms=100, provenance_score=0.9,
    )
    r1.metrics = {"entity_f1": 0.8, "keyword_coverage": 0.7}
    return EvaluationReport(
        system_name="test",
        total_queries=2,
        successful_queries=1,
        metrics_summary={"entity_f1": 0.8, "keyword_coverage": 0.7, "latency_ms": 100.0},
        metrics_by_category={"FACTUAL": {"entity_f1": 0.8}},
        failures=["t2"],
        results=[r1],
    )


class TestEvaluationReport:
    """Test EvaluationReport."""

    def test_to_json_valid(self):
        report = _make_report()
        raw = report.to_json()
        data = json.loads(raw)
        assert data["system_name"] == "test"
        assert data["total_queries"] == 2
        assert data["successful_queries"] == 1
        assert len(data["results"]) == 1
        assert data["failures"] == ["t2"]

    def test_to_markdown_contains_headers(self):
        report = _make_report()
        md = report.to_markdown()
        assert "# Evaluation Report: test" in md
        assert "## Summary Metrics" in md
        assert "## Per-Category Breakdown" in md
        assert "## Failures" in md

    def test_to_markdown_contains_metric_values(self):
        report = _make_report()
        md = report.to_markdown()
        assert "entity_f1" in md
        assert "keyword_coverage" in md

    def test_to_console_contains_summary(self):
        report = _make_report()
        out = report.to_console()
        assert "=== Evaluation: test ===" in out
        assert "1/2 successful" in out
        assert "entity_f1" in out

    def test_to_console_shows_failures(self):
        report = _make_report()
        out = report.to_console()
        assert "t2" in out

    def test_to_markdown_with_comparison(self):
        report = _make_report()
        report.comparison = {
            "plain_rag": {"entity_f1": 0.5},
            "hybrid_full": {"entity_f1": 0.9},
        }
        md = report.to_markdown()
        assert "## Baseline Comparison" in md
        assert "plain_rag" in md
        assert "hybrid_full" in md

    def test_to_json_truncates_answer(self):
        r1 = EvalResult(
            query_id="t1", category="TEST", question="q1",
            answer="x" * 500, latency_ms=50,
        )
        r1.metrics = {}
        report = EvaluationReport(
            system_name="test", total_queries=1, successful_queries=1,
            results=[r1],
        )
        data = json.loads(report.to_json())
        assert len(data["results"][0]["answer"]) == 200

    def test_timestamp_is_set(self):
        report = _make_report()
        assert report.timestamp
