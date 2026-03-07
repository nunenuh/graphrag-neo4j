"""
Graph API endpoints for schema and exploration.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.core.logging import get_logger
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

logger = get_logger(__name__)
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
    usecase = GraphUseCase(client)

    try:
        labels, rels = usecase.get_schema()
        return GraphSchemaResponse(node_labels=labels, relationship_types=rels)

    except RepositoryException as e:
        logger.error("Graph schema error", error=str(e))
        raise HTTPException(status_code=503, detail=_error_detail("graph_schema_error", e))


@router.get("/explore", response_model=GraphExploreResponse)
async def explore(
    limit: int = Query(50, ge=1, le=200, description="Max relationships to return"),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Explore a sample of the knowledge graph."""
    usecase = GraphUseCase(client)

    try:
        nodes, edges = usecase.explore(limit=limit)
        return GraphExploreResponse(nodes=nodes, edges=edges)

    except RepositoryException as e:
        logger.error("Graph explore error", error=str(e))
        raise HTTPException(status_code=503, detail=_error_detail("graph_explore_error", e))


@router.get("/stats", response_model=GraphStatsResponse)
async def get_stats(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get graph statistics (node/edge counts per type)."""
    usecase = GraphUseCase(client)
    try:
        return GraphStatsResponse(**usecase.get_stats())
    except RepositoryException as e:
        logger.error("Graph stats error", error=str(e))
        raise HTTPException(status_code=503, detail=_error_detail("graph_stats_error", e))


@router.get("/nodes/{uid}", response_model=NodeDetailResponse)
async def get_node(uid: str, client: Neo4jClient = Depends(get_neo4j_client)):
    """Get a single node by UID with its relationships."""
    usecase = GraphUseCase(client)
    try:
        result = usecase.get_node(uid)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Node '{uid}' not found")
        return NodeDetailResponse(**result)
    except RepositoryException as e:
        logger.error("Node detail error", error=str(e))
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
    usecase = GraphUseCase(client)
    try:
        results = usecase.search_nodes(q, label=label, limit=limit)
        return NodeSearchResponse(
            results=[NodeSearchResultOut(**r) for r in results],
            count=len(results),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RepositoryException as e:
        logger.error("Node search error", error=str(e))
        raise HTTPException(status_code=503, detail=_error_detail("node_search_error", e))
