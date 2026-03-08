"""Pydantic schemas for the analytics module."""

from pydantic import BaseModel, Field


class AnalyticsRunResponse(BaseModel):
    """Response for POST /api/v1/analytics/run."""

    communities_detected: int = Field(description="Number of communities found")
    authors_with_centrality: int = Field(description="Authors with centrality metrics")
    methods_with_trends: int = Field(description="Methods with trend scores")
    tasks_with_trends: int = Field(description="Tasks with trend scores")
    message: str


class CommunityOut(BaseModel):
    """Single community info."""

    community_id: int
    member_count: int
    top_members: list[dict] = Field(default_factory=list)


class CommunitiesResponse(BaseModel):
    """Response for GET /api/v1/analytics/communities."""

    total_communities: int
    communities: list[CommunityOut]


class TrendingItem(BaseModel):
    """Single trending method/task."""

    uid: str
    name: str
    trend_score: float


class TrendsResponse(BaseModel):
    """Response for GET /api/v1/analytics/trends."""

    entity_type: str
    items: list[TrendingItem]
