"""Pydantic schemas for evaluation API endpoints."""

from pydantic import BaseModel, Field


class EvalQueryOut(BaseModel):
    id: str
    category: str
    question: str
    difficulty: str
    expected_entities: list[str] = Field(default_factory=list)
    min_hops: int = 1


class EvalQueriesResponse(BaseModel):
    queries: list[EvalQueryOut]
    count: int


class EvalResultOut(BaseModel):
    query_id: str
    category: str
    question: str
    answer: str
    latency_ms: int = 0
    query_type: str = ""
    retrieval_strategy: str = ""
    provenance_score: float = 0.0
    metrics: dict[str, float] = Field(default_factory=dict)


class EvalReportResponse(BaseModel):
    timestamp: str
    system_name: str
    total_queries: int
    successful_queries: int
    metrics_summary: dict[str, float] = Field(default_factory=dict)
    metrics_by_category: dict[str, dict[str, float]] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    comparison: dict[str, dict] | None = None
    results: list[EvalResultOut] = Field(default_factory=list)
