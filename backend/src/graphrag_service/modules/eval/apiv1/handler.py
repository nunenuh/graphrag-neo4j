"""Evaluation API endpoints."""

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.modules.rag.usecase import RAGUseCase
from loguru import logger

from ..schemas import EvalQueriesResponse, EvalQueryOut, EvalReportResponse, EvalResultOut

router = APIRouter()

# Cached report path
_REPORT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "data"


def _get_report_path() -> Path:
    return _REPORT_DIR / "eval_report_latest.json"


def _get_all_queries():
    """Import and return all evaluation queries."""
    from tests.evaluation.queries import ALL_QUERIES
    return ALL_QUERIES


@router.get("/queries", response_model=EvalQueriesResponse)
async def list_eval_queries(
    category: str | None = Query(None, description="Filter by category"),
):
    """List all 40 evaluation queries (optionally filtered by category)."""
    try:
        queries = _get_all_queries()
    except ImportError:
        raise HTTPException(status_code=500, detail="Evaluation queries not available")

    if category:
        queries = [q for q in queries if q.category == category]

    return EvalQueriesResponse(
        queries=[
            EvalQueryOut(
                id=q.id,
                category=q.category,
                question=q.question,
                difficulty=q.difficulty,
                expected_entities=q.expected_entities,
                min_hops=q.min_hops,
            )
            for q in queries
        ],
        count=len(queries),
    )


@router.post("/run", response_model=EvalReportResponse)
async def run_evaluation(
    category: str | None = Query(None, description="Run only specific category"),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Run evaluation suite and return report. Results are cached to disk."""
    try:
        from tests.evaluation.queries import ALL_QUERIES
        from tests.evaluation.runner import EvaluationRunner
    except ImportError:
        raise HTTPException(status_code=500, detail="Evaluation framework not available")

    queries = ALL_QUERIES
    if category:
        queries = [q for q in queries if q.category == category]

    if not queries:
        raise HTTPException(status_code=400, detail=f"No queries for category: {category}")

    usecase = RAGUseCase(client)
    runner = EvaluationRunner(pipeline_fn=usecase.query, queries=queries)

    logger.info(f"eval.api.run_start queries={len(queries)}")
    report = runner.run_all(system_name="graphrag")

    # Cache report to disk
    report_path = _get_report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_json())
    logger.info(f"eval.api.run_done saved={report_path}")

    return _report_to_response(report)


@router.get("/report/latest", response_model=EvalReportResponse)
async def get_latest_report():
    """Get the latest cached evaluation report."""
    report_path = _get_report_path()
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="No evaluation report found. Run /eval/run first.")

    try:
        data = json.loads(report_path.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")

    return EvalReportResponse(
        timestamp=data.get("timestamp", ""),
        system_name=data.get("system_name", ""),
        total_queries=data.get("total_queries", 0),
        successful_queries=data.get("successful_queries", 0),
        metrics_summary=data.get("metrics_summary", {}),
        metrics_by_category=data.get("metrics_by_category", {}),
        failures=data.get("failures", []),
        comparison=data.get("comparison"),
        results=[
            EvalResultOut(**r) for r in data.get("results", [])
        ],
    )


def _report_to_response(report) -> EvalReportResponse:
    """Convert EvaluationReport to API response."""
    return EvalReportResponse(
        timestamp=report.timestamp,
        system_name=report.system_name,
        total_queries=report.total_queries,
        successful_queries=report.successful_queries,
        metrics_summary=report.metrics_summary,
        metrics_by_category=report.metrics_by_category,
        failures=report.failures,
        comparison=report.comparison,
        results=[
            EvalResultOut(
                query_id=r.query_id,
                category=r.category,
                question=r.question,
                answer=r.answer[:200],
                latency_ms=r.latency_ms,
                query_type=r.query_type,
                retrieval_strategy=r.retrieval_strategy,
                provenance_score=r.provenance_score,
                metrics=r.metrics,
            )
            for r in report.results
        ],
    )
