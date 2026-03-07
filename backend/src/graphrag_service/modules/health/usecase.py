"""
Health use case orchestration layer.
"""

from typing import List, Tuple

from .schemas import ComponentHealth
from .services import HealthService, get_health_service


class HealthUseCase:
    """Use case for orchestrating health check operations."""

    def __init__(self):
        self.service = get_health_service()

    def get_basic_health(
        self,
    ) -> Tuple[str, List[ComponentHealth], float]:
        """Get basic health status with component checks."""
        return self.service.get_basic_health()
