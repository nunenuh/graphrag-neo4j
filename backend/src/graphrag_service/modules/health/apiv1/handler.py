"""
Health check API endpoints.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger

from ..schemas import HealthStatusResponse, PingResponse
from ..usecase import HealthUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.get("/ping", response_model=PingResponse)
async def ping():
    """Simple ping endpoint for liveness checks."""
    return PingResponse(status="ok", timestamp=datetime.now(UTC), message="pong")


@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status():
    """Get basic health status with dependency checks."""
    usecase = HealthUseCase()

    try:
        overall_status, components, uptime = usecase.get_basic_health()

        return HealthStatusResponse(
            status=overall_status,
            timestamp=datetime.now(UTC),
            version=get_settings().APP_VERSION,
            components=components,
            uptime_seconds=uptime,
        )

    except Exception as e:
        logger.error(f"Health status check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "health_check_failed",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
