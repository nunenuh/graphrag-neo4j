"""Evaluation runner — orchestrates running queries and computing metrics."""

import time
from typing import Callable

from loguru import logger

from .metrics import EvalResult, aggregate_metrics, compute_query_metrics
from .queries import EvalQuery
from .report import EvaluationReport


class EvaluationRunner:
    """Runs evaluation queries through a pipeline and computes metrics."""

    def __init__(
        self,
        pipeline_fn: Callable[[str], dict],
        queries: list[EvalQuery],
    ):
        """Initialize with a pipeline function and queries.

        Args:
            pipeline_fn: Callable that takes a question string and returns
                the full RAGState dict.
            queries: List of evaluation queries with gold standards.
        """
        self.pipeline_fn = pipeline_fn
        self.queries = queries

    def run_single(self, query: EvalQuery) -> EvalResult:
        """Run a single evaluation query.

        Returns EvalResult with computed metrics.
        """
        t0 = time.perf_counter()
        try:
            state = self.pipeline_fn(query.question)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            result = EvalResult(
                query_id=query.id,
                category=query.category,
                question=query.question,
                answer=state.get("answer", ""),
                seed_nodes=state.get("seed_nodes", []),
                subgraph=state.get("subgraph", {}),
                latency_ms=latency_ms,
                query_type=state.get("query_type", ""),
                retrieval_strategy=state.get("retrieval_strategy", ""),
                provenance_score=state.get("provenance_score", 0.0),
                unsupported_claims=state.get("unsupported_claims", []),
            )

            result.metrics = compute_query_metrics(
                result,
                expected_entities=query.expected_entities,
                gold_keywords=query.gold_answer_keywords,
            )

            logger.bind(
                query_id=query.id,
                latency_ms=latency_ms,
                metrics=result.metrics,
            ).info("eval.query_done")

            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.bind(
                query_id=query.id,
                error=str(e),
                latency_ms=latency_ms,
            ).error("eval.query_failed")

            result = EvalResult(
                query_id=query.id,
                category=query.category,
                question=query.question,
                answer=f"ERROR: {e}",
                latency_ms=latency_ms,
            )
            result.metrics = {"error": 1.0}
            return result

    def run_all(self, system_name: str = "graphrag") -> EvaluationReport:
        """Run all queries and produce an evaluation report.

        Args:
            system_name: Name for this evaluation run.

        Returns:
            EvaluationReport with aggregated metrics.
        """
        logger.bind(
            total_queries=len(self.queries),
            system=system_name,
        ).info("eval.start")

        results: list[EvalResult] = []
        failures: list[str] = []

        for query in self.queries:
            result = self.run_single(query)
            results.append(result)
            if "error" in result.metrics:
                failures.append(query.id)

        metrics_summary = aggregate_metrics(results)

        # Per-category breakdown
        categories = set(q.category for q in self.queries)
        metrics_by_category: dict[str, dict[str, float]] = {}
        for cat in categories:
            cat_results = [r for r in results if r.category == cat]
            metrics_by_category[cat] = aggregate_metrics(cat_results)

        report = EvaluationReport(
            system_name=system_name,
            total_queries=len(self.queries),
            successful_queries=len(self.queries) - len(failures),
            metrics_summary=metrics_summary,
            metrics_by_category=metrics_by_category,
            failures=failures,
            results=results,
        )

        logger.bind(
            total=report.total_queries,
            successful=report.successful_queries,
            failures=len(failures),
        ).info("eval.done")

        return report
