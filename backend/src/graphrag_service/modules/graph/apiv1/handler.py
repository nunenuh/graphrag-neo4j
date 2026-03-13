"""
Graph API endpoints for schema and exploration.
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from loguru import logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException

from ..schemas import (
    GraphExploreResponse,
    GraphSchemaResponse,
    GraphStatsResponse,
    NodeDetailResponse,
    NodeSearchResponse,
    NodeSearchResultOut,
)
from ..usecase import GraphUseCase

router = APIRouter()


def _error_detail(error_code: str, exc: Exception) -> dict:
    """Build error detail dict, hiding internals in non-debug mode."""
    return {
        "error": error_code,
        "message": str(exc) if get_settings().APP_DEBUG else "A service error occurred",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/schema", response_model=GraphSchemaResponse)
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get Neo4j graph schema (node labels and relationship types)."""
    logger.info("graph.schema.request")
    usecase = GraphUseCase(client)
    t0 = time.perf_counter()

    try:
        labels, rels = usecase.get_schema()
        logger.bind(labels=len(labels), rels=len(rels), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("graph.schema.response")
        return GraphSchemaResponse(node_labels=labels, relationship_types=rels)

    except RepositoryException as e:
        logger.bind(error=str(e), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).error("graph.schema.error")
        raise HTTPException(status_code=503, detail=_error_detail("graph_schema_error", e))


@router.get("/explore", response_model=GraphExploreResponse)
async def explore(
    limit: int = Query(50, ge=1, le=1000, description="Max relationships to return"),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Explore a sample of the knowledge graph."""
    logger.bind(limit=limit).info("graph.explore.request")
    usecase = GraphUseCase(client)
    t0 = time.perf_counter()

    try:
        nodes, edges = usecase.explore(limit=limit)
        logger.bind(nodes=len(nodes), edges=len(edges), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("graph.explore.response")
        return GraphExploreResponse(nodes=nodes, edges=edges)

    except RepositoryException as e:
        logger.bind(error=str(e), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).error("graph.explore.error")
        raise HTTPException(status_code=503, detail=_error_detail("graph_explore_error", e))


@router.get("/stats", response_model=GraphStatsResponse)
async def get_stats(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get graph statistics (node/edge counts per type)."""
    logger.info("graph.stats.request")
    usecase = GraphUseCase(client)
    t0 = time.perf_counter()
    try:
        stats = usecase.get_stats()
        logger.bind(duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("graph.stats.response")
        return GraphStatsResponse(**stats)
    except RepositoryException as e:
        logger.bind(error=str(e), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).error("graph.stats.error")
        raise HTTPException(status_code=503, detail=_error_detail("graph_stats_error", e))


@router.get("/nodes/{uid}", response_model=NodeDetailResponse)
async def get_node(uid: str, client: Neo4jClient = Depends(get_neo4j_client)):
    """Get a single node by UID with its relationships."""
    logger.bind(uid=uid).info("graph.node.request")
    usecase = GraphUseCase(client)
    t0 = time.perf_counter()
    try:
        result = usecase.get_node(uid)
        if result is None:
            logger.bind(uid=uid).info("graph.node.not_found")
            raise HTTPException(status_code=404, detail=f"Node '{uid}' not found")
        logger.bind(uid=uid, duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("graph.node.response")
        return NodeDetailResponse(**result)
    except RepositoryException as e:
        logger.bind(uid=uid, error=str(e), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).error("graph.node.error")
        raise HTTPException(status_code=503, detail=_error_detail("node_detail_error", e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=NodeSearchResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    label: str | None = Query(None, description="Filter by label (Paper, Method, Task, Dataset)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Search nodes by name (case-insensitive)."""
    logger.bind(query=q, label=label, limit=limit).info("graph.search.request")
    usecase = GraphUseCase(client)
    t0 = time.perf_counter()
    try:
        results = usecase.search_nodes(q, label=label, limit=limit)
        logger.bind(count=len(results), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).info("graph.search.response")
        return NodeSearchResponse(
            results=[NodeSearchResultOut(**r) for r in results],
            count=len(results),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RepositoryException as e:
        logger.bind(error=str(e), duration_ms=round((time.perf_counter() - t0) * 1000, 1)).error("graph.search.error")
        raise HTTPException(status_code=503, detail=_error_detail("node_search_error", e))
