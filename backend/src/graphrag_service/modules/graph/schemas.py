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


class GraphStatsResponse(BaseModel):
    """Graph statistics."""

    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")
    node_counts: dict[str, int] = Field(..., description="Node count per label")
    edge_counts: dict[str, int] = Field(..., description="Edge count per type")


class NodeRelationOut(BaseModel):
    """A related node reference."""

    uid: str = Field(default="", description="Related node ID")
    type: str = Field(default="", description="Relationship type")


class NodeDetailResponse(BaseModel):
    """Detailed node information."""

    uid: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label")
    properties: dict = Field(default_factory=dict, description="Node properties")
    outgoing: list[dict] = Field(default_factory=list, description="Outgoing relationships")
    incoming: list[dict] = Field(default_factory=list, description="Incoming relationships")


class NodeSearchResultOut(BaseModel):
    """A node search result."""

    uid: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label")
    name: str = Field(..., description="Node name")
    properties: dict = Field(default_factory=dict, description="Node properties")


class NodeSearchResponse(BaseModel):
    """Node search response."""

    results: list[NodeSearchResultOut] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
