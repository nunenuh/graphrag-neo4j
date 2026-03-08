"""Pydantic schemas for the entity resolution module."""

from pydantic import BaseModel, Field


class ERStatsResponse(BaseModel):
    """Response for GET /api/v1/er/stats."""

    total_authors: int = Field(description="Total Author nodes in the graph")
    merged_authors: int = Field(description="Authors that were merged into another")
    canonical_authors: int = Field(description="Authors that are canonical (not merged)")
    total_authored_rels: int = Field(description="Total AUTHORED relationships")
    clusters_found: int = Field(description="Number of clusters found in last resolution")


class ERResolveResponse(BaseModel):
    """Response for POST /api/v1/er/resolve."""

    blocks_processed: int
    clusters_found: int
    authors_merged: int
    message: str
