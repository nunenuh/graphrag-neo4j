"""
Health check service with dependency checks.
"""

import time
from typing import List, Tuple

from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.core.logging import get_logger

from .schemas import ComponentHealth

logger = get_logger(__name__)

_start_time = time.time()


class HealthService:
    """Service for performing health checks."""

    def check_neo4j(self) -> ComponentHealth:
        """Check Neo4j connectivity."""
        t0 = time.time()
        try:
            client = get_neo4j_client()
            connected = client.verify_connection()
            elapsed = (time.time() - t0) * 1000
            return ComponentHealth(
                name="neo4j",
                status="healthy" if connected else "unhealthy",
                message="Connected" if connected else "Connection failed",
                response_time_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            logger.error("Neo4j health check failed", error=str(e))
            return ComponentHealth(
                name="neo4j",
                status="unhealthy",
                message=str(e),
                response_time_ms=round(elapsed, 2),
            )

    def get_basic_health(
        self,
    ) -> Tuple[str, List[ComponentHealth], float]:
        """Get basic health status with component checks."""
        components = [self.check_neo4j()]
        overall = (
            "healthy"
            if all(c.status == "healthy" for c in components)
            else "unhealthy"
        )
        uptime = time.time() - _start_time
        return overall, components, uptime


_health_service: HealthService | None = None


def get_health_service() -> HealthService:
    """Get health service singleton instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
