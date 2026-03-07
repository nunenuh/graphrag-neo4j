"""
Graph API endpoints for schema and exploration.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

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


@router.get("/schema", response_model=GraphSchemaResponse)
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get Neo4j graph schema (node labels and relationship types)."""
    usecase = GraphUseCase(client)

    try:
        labels, rels = usecase.get_schema()
        return GraphSchemaResponse(node_labels=labels, relationship_types=rels)

    except RepositoryException as e:
        logger.error(f"Graph schema error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "graph_schema_error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@router.get("/explore", response_model=GraphExploreResponse)
async def explore(
    limit: int = Query(50, ge=1, le=500, description="Max relationships to return"),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    """Explore a sample of the knowledge graph."""
    usecase = GraphUseCase(client)

    try:
        nodes, edges = usecase.explore(limit=limit)
        return GraphExploreResponse(nodes=nodes, edges=edges)

    except RepositoryException as e:
        logger.error(f"Graph explore error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "graph_explore_error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_stats(client: Neo4jClient = Depends(get_neo4j_client)):
    """Get graph statistics (node/edge counts per type)."""
    usecase = GraphUseCase(client)
    try:
        return GraphStatsResponse(**usecase.get_stats())
    except RepositoryException as e:
        logger.error(f"Graph stats error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "graph_stats_error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


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
        logger.error(f"Node detail error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "node_detail_error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@router.get("/search", response_model=NodeSearchResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, description="Search query"),
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
    except RepositoryException as e:
        logger.error(f"Node search error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "node_search_error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
