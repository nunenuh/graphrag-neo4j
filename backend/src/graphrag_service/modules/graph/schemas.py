"""
Graph module response schemas.
"""

from pydantic import BaseModel, Field


class GraphSchemaResponse(BaseModel):
    """Schema information from Neo4j."""

    node_labels: list[str] = Field(..., description="All node labels in the graph")
    relationship_types: list[str] = Field(
        ..., description="All relationship types in the graph"
    )


class GraphNodeOut(BaseModel):
    """A node from the graph exploration."""

    id: str = Field(default="", description="Node ID")
    label: str = Field(default="Node", description="Node label")
    name: str = Field(default="", description="Node name or title")
    properties: dict = Field(default_factory=dict, description="Node properties")


class GraphEdgeOut(BaseModel):
    """An edge from the graph exploration."""

    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")


class GraphExploreResponse(BaseModel):
    """Graph exploration response."""

    nodes: list[dict] = Field(..., description="List of nodes")
    edges: list[GraphEdgeOut] = Field(..., description="List of edges")
