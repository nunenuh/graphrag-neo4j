"""
Graph API endpoints for schema and exploration.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException

from ..schemas import GraphExploreResponse, GraphSchemaResponse
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
