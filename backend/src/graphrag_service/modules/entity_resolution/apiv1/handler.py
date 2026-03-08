"""Entity resolution API endpoints."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException
from loguru import logger

from ..schemas import ERResolveResponse, ERStatsResponse
from ..usecase import ERUseCase

router = APIRouter()


def _error_detail(error_code: str, exc: Exception) -> dict:
    return {
        "error": error_code,
        "message": str(exc) if get_settings().APP_DEBUG else "A service error occurred",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/stats", response_model=ERStatsResponse)
async def get_er_stats(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get entity resolution statistics."""
    logger.info("er.stats.request")
    usecase = ERUseCase(client)
    t0 = time.perf_counter()
    try:
        stats = usecase.get_stats()
        logger.bind(duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("er.stats.response")
        return ERStatsResponse(**stats)
    except RepositoryException as e:
        logger.bind(error=str(e)).error("er.stats.error")
        raise HTTPException(status_code=503, detail=_error_detail("er_stats_error", e))


@router.post("/resolve", response_model=ERResolveResponse)
async def resolve_authors(client: Neo4jClient = Depends(get_neo4j_client)):
    """Run entity resolution on Author nodes."""
    logger.info("er.resolve.request")
    usecase = ERUseCase(client)
    t0 = time.perf_counter()
    try:
        result = usecase.resolve()
        duration = round((time.perf_counter() - t0) * 1000, 1)
        logger.bind(duration_ms=duration, **result).info("er.resolve.response")
        return ERResolveResponse(
            **result,
            message=f"Resolved in {duration}ms",
        )
    except RepositoryException as e:
        logger.bind(error=str(e)).error("er.resolve.error")
        raise HTTPException(status_code=503, detail=_error_detail("er_resolve_error", e))
