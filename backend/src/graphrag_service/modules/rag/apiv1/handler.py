"""
RAG query API endpoint.
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import get_neo4j_client
from loguru import logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import ServiceException

from ..schemas import EdgeOut, QueryRequest, QueryResponse, SeedNodeOut
from ..usecase import RAGUseCase

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, client: Neo4jClient = Depends(get_neo4j_client)):
    """
    Ask a question to the knowledge graph.

    Embeds the question, performs vector search across all node types,
    traverses the graph from seed nodes, and generates a grounded answer.
    """
    logger.bind(question=req.question[:120]).info("rag.request")
    usecase = RAGUseCase(client)

    t0 = time.time()
    try:
        result = usecase.query(req.question)
        subgraph = result.get("subgraph", {})
        latency_ms = int((time.time() - t0) * 1000)

        response = QueryResponse(
            answer=result["answer"],
            seed_nodes=[
                SeedNodeOut(
                    id=s["id"], label=s["label"], name=s["name"], score=s["score"]
                )
                for s in subgraph.get("seed_nodes", [])
            ],
            nodes=subgraph.get("nodes", []),
            edges=[
                EdgeOut(
                    from_id=e["from_id"],
                    to_id=e["to_id"],
                    type=e["type"],
                    properties=e.get("properties", {}),
                )
                for e in subgraph.get("edges", [])
            ],
            cypher_used=subgraph.get("cypher_used", ""),
            latency_ms=latency_ms,
        )
        logger.bind(
            latency_ms=latency_ms,
            seed_count=len(response.seed_nodes),
            node_count=len(response.nodes),
            edge_count=len(response.edges),
            answer_len=len(response.answer),
        ).info("rag.response")
        return response

    except ServiceException as e:
        latency_ms = int((time.time() - t0) * 1000)
        logger.bind(error=str(e), latency_ms=latency_ms).error("rag.service_error")
        msg = str(e) if get_settings().APP_DEBUG else "A service error occurred"
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_error",
                "message": msg,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        logger.opt(exception=True).bind(error=str(e), latency_ms=latency_ms).error("rag.internal_error")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
