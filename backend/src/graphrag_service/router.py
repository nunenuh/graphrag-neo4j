"""
Main API router that aggregates all service endpoints.
"""

from fastapi import APIRouter, Depends

from .core.auth import get_api_key
from .modules.analytics.apiv1.handler import router as analytics_router
from .modules.entity_resolution.apiv1.handler import router as er_router
from .modules.graph.apiv1.handler import router as graph_router
from .modules.health.apiv1.handler import router as health_router
from .modules.rag.apiv1.handler import router as rag_router

api_router = APIRouter()

# Health endpoints — no auth required
api_router.include_router(health_router, prefix="/v1/health", tags=["Health"])

# Protected endpoints — require X-API-Key header
api_router.include_router(
    graph_router, prefix="/v1/graph", tags=["Graph"], dependencies=[Depends(get_api_key)]
)
api_router.include_router(
    rag_router, prefix="/v1/rag", tags=["RAG"], dependencies=[Depends(get_api_key)]
)
api_router.include_router(
    er_router, prefix="/v1/er", tags=["Entity Resolution"], dependencies=[Depends(get_api_key)]
)
api_router.include_router(
    analytics_router, prefix="/v1/analytics", tags=["Analytics"], dependencies=[Depends(get_api_key)]
)
