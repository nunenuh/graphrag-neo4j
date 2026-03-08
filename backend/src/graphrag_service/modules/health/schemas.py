"""
Health check response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    """Simple ping response for liveness checks."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    message: str = Field(..., description="Status message")


class Neo4jPingResponse(BaseModel):
    """Neo4j connectivity check response."""

    status: str = Field(..., description="Neo4j status (healthy/unhealthy)")
    message: str = Field(..., description="Status message")
    response_time_ms: float = Field(..., description="Neo4j response time in milliseconds")
    timestamp: datetime = Field(..., description="Response timestamp")


class ComponentHealth(BaseModel):
    """Health status of a service component."""

    name: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status (healthy/unhealthy)")
    message: Optional[str] = Field(None, description="Status message or error details")
    response_time_ms: Optional[float] = Field(
        None, description="Component response time in milliseconds"
    )


class HealthStatusResponse(BaseModel):
    """Basic health status response with dependencies."""

    status: str = Field(..., description="Overall service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="Service version")
    components: list[ComponentHealth] = Field(
        ..., description="Component health statuses"
    )
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
