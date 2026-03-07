"""
Main API router that aggregates all service endpoints.
"""

from fastapi import APIRouter

from .modules.graph.apiv1.handler import router as graph_router
from .modules.health.apiv1.handler import router as health_router
from .modules.rag.apiv1.handler import router as rag_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/v1/health", tags=["Health"])
api_router.include_router(graph_router, prefix="/v1/graph", tags=["Graph"])
api_router.include_router(rag_router, prefix="/v1/rag", tags=["RAG"])
