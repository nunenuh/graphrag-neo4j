"""Evaluation report generation — JSON, Markdown, console output."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .metrics import EvalResult


@dataclass
class EvaluationReport:
    """Complete evaluation report."""

    system_name: str
    total_queries: int
    successful_queries: int
    metrics_summary: dict[str, float] = field(default_factory=dict)
    metrics_by_category: dict[str, dict[str, float]] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    results: list[EvalResult] = field(default_factory=list)
    comparison: dict[str, dict] | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> str:
        """Serialize report to JSON string."""
        data = {
            "timestamp": self.timestamp,
            "system_name": self.system_name,
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "metrics_summary": self.metrics_summary,
            "metrics_by_category": self.metrics_by_category,
            "failures": self.failures,
            "comparison": self.comparison,
            "results": [
                {
                    "query_id": r.query_id,
                    "category": r.category,
                    "question": r.question,
                    "answer": r.answer[:200],
                    "latency_ms": r.latency_ms,
                    "query_type": r.query_type,
                    "retrieval_strategy": r.retrieval_strategy,
                    "provenance_score": r.provenance_score,
                    "metrics": r.metrics,
                }
                for r in self.results
            ],
        }
        return json.dumps(data, indent=2, default=str)

    def to_markdown(self) -> str:
        """Generate markdown report table."""
        lines = [
            f"# Evaluation Report: {self.system_name}",
            f"**Date**: {self.timestamp}",
            f"**Queries**: {self.successful_queries}/{self.total_queries} successful",
            "",
            "## Summary Metrics",
            "",
            "| Metric | Score |",
            "|--------|-------|",
        ]

        for metric, score in sorted(self.metrics_summary.items()):
            if "latency" in metric:
                lines.append(f"| {metric} | {score:.0f} ms |")
            else:
                lines.append(f"| {metric} | {score:.4f} |")

        lines.extend(["", "## Per-Category Breakdown", ""])

        for category, metrics in sorted(self.metrics_by_category.items()):
            lines.append(f"### {category}")
            lines.append("")
            lines.append("| Metric | Score |")
            lines.append("|--------|-------|")
            for metric, score in sorted(metrics.items()):
                if "latency" in metric:
                    lines.append(f"| {metric} | {score:.0f} ms |")
                else:
                    lines.append(f"| {metric} | {score:.4f} |")
            lines.append("")

        if self.failures:
            lines.extend([
                "## Failures",
                "",
                "| Query ID |",
                "|----------|",
            ])
            for qid in self.failures:
                lines.append(f"| {qid} |")

        if self.comparison:
            lines.extend(["", "## Baseline Comparison", ""])
            baselines = sorted(self.comparison.keys())
            header = "| Metric | " + " | ".join(baselines) + " |"
            separator = "|--------|" + "|".join(["-------"] * len(baselines)) + "|"
            lines.extend([header, separator])

            all_metrics = set()
            for baseline_metrics in self.comparison.values():
                all_metrics.update(baseline_metrics.keys())

            for metric in sorted(all_metrics):
                row = f"| {metric} |"
                for baseline in baselines:
                    val = self.comparison[baseline].get(metric, 0.0)
                    if "latency" in metric:
                        row += f" {val:.0f} ms |"
                    else:
                        row += f" {val:.4f} |"
                lines.append(row)

        return "\n".join(lines)

    def to_console(self) -> str:
        """Generate concise console summary."""
        lines = [
            f"=== Evaluation: {self.system_name} ===",
            f"Queries: {self.successful_queries}/{self.total_queries} successful",
            "",
            "Metrics:",
        ]

        for metric, score in sorted(self.metrics_summary.items()):
            if "latency" in metric:
                lines.append(f"  {metric:<25} {score:>8.0f} ms")
            else:
                lines.append(f"  {metric:<25} {score:>8.4f}")

        if self.failures:
            lines.append(f"\nFailures ({len(self.failures)}): {', '.join(self.failures)}")

        return "\n".join(lines)
