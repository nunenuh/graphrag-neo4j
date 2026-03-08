"""Analytics API endpoints."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException
from loguru import logger

from ..schemas import (
    AnalyticsRunResponse,
    CommunitiesResponse,
    CommunityOut,
    TrendingItem,
    TrendsResponse,
)
from ..usecase import AnalyticsUseCase

router = APIRouter()


def _error_detail(error_code: str, exc: Exception) -> dict:
    return {
        "error": error_code,
        "message": str(exc) if get_settings().APP_DEBUG else "A service error occurred",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/run", response_model=AnalyticsRunResponse)
async def run_analytics(client: Neo4jClient = Depends(get_neo4j_client)):
    """Run the full analytics pipeline (community detection, centrality, trends)."""
    logger.info("analytics.run.request")
    usecase = AnalyticsUseCase(client)
    t0 = time.perf_counter()
    try:
        result = usecase.run_all()
        duration = round((time.perf_counter() - t0) * 1000, 1)
        logger.bind(duration_ms=duration, **result).info("analytics.run.response")
        return AnalyticsRunResponse(
            **result,
            message=f"Analytics pipeline completed in {duration}ms",
        )
    except RepositoryException as e:
        logger.bind(error=str(e)).error("analytics.run.error")
        raise HTTPException(status_code=503, detail=_error_detail("analytics_run_error", e))


@router.get("/communities", response_model=CommunitiesResponse)
async def get_communities(
    limit: int = Query(50, ge=1, le=200),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """List detected communities with member counts."""
    usecase = AnalyticsUseCase(client)
    try:
        rows = usecase.get_communities(limit=limit)
        communities = [
            CommunityOut(
                community_id=r["cid"],
                member_count=r["member_count"],
                top_members=r.get("top_members", []),
            )
            for r in rows
        ]
        return CommunitiesResponse(
            total_communities=len(communities),
            communities=communities,
        )
    except RepositoryException as e:
        raise HTTPException(status_code=503, detail=_error_detail("communities_error", e))


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    type: str = Query("Method", description="Entity type: Method or Task"),
    limit: int = Query(10, ge=1, le=100),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Get top trending methods or tasks."""
    if type not in ("Method", "Task"):
        raise HTTPException(status_code=400, detail="type must be 'Method' or 'Task'")
    usecase = AnalyticsUseCase(client)
    try:
        rows = usecase.get_trending(entity_type=type, limit=limit)
        items = [
            TrendingItem(uid=r["uid"], name=r["name"], trend_score=r["trend_score"])
            for r in rows
        ]
        return TrendsResponse(entity_type=type, items=items)
    except RepositoryException as e:
        raise HTTPException(status_code=503, detail=_error_detail("trends_error", e))
