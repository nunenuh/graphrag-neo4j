"""
RAG module response schemas.
"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """RAG query request."""

    question: str = Field(..., min_length=1, description="The question to ask")


class SeedNodeOut(BaseModel):
    """A seed node found by vector search."""

    id: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label (Paper, Method, Task, Dataset)")
    name: str = Field(..., description="Node name or title")
    score: float | None = Field(None, description="Similarity score")


class EdgeOut(BaseModel):
    """A relationship in the retrieved subgraph."""

    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")
    properties: dict = Field(default_factory=dict, description="Edge properties")


class QueryResponse(BaseModel):
    """RAG query response with answer and graph context."""

    answer: str = Field(..., description="LLM-generated answer")
    seed_nodes: list[SeedNodeOut] = Field(
        ..., description="Seed nodes from vector search"
    )
    nodes: list[dict] = Field(..., description="All nodes in retrieved subgraph")
    edges: list[EdgeOut] = Field(
        ..., description="All edges in retrieved subgraph"
    )
    cypher_used: str = Field(..., description="Cypher query used for traversal")
    latency_ms: int = Field(..., description="Total latency in milliseconds")
