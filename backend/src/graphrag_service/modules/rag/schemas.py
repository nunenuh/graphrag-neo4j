"""
RAG module response schemas.
"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """RAG query request."""

    question: str = Field(..., min_length=1, max_length=2000, description="The question to ask")
    depth: int | None = Field(None, ge=1, le=4, description="Traversal depth (1-4 hops). If omitted, auto-selected by query type.")


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


class TraversalStep(BaseModel):
    """A single hop in the graph traversal path."""

    hop: int = Field(..., description="Hop number (0=seed, 1=first hop, 2=second hop)")
    node_count: int = Field(..., description="Number of nodes discovered at this hop")
    node_labels: list[str] = Field(default_factory=list, description="Node labels at this hop")
    label_counts: dict[str, int] = Field(default_factory=dict, description="Count per node label")
    edge_types: list[str] = Field(default_factory=list, description="Relationship types traversed")
    description: str = Field(..., description="Human-readable description of this hop")


class PipelineMetadata(BaseModel):
    """Detailed pipeline execution metadata for evaluation."""

    llm_provider: str = Field(..., description="LLM provider name")
    llm_model: str = Field(..., description="LLM model name")
    embedding_provider: str = Field(..., description="Embedding provider name")
    embedding_model: str = Field(..., description="Embedding model name")
    embedding_dim: int = Field(..., description="Embedding dimension")
    top_k: int = Field(..., description="Top-K seed nodes requested")
    traversal_depth: int = Field(..., description="Graph traversal depth")
    seed_count: int = Field(..., description="Number of seed nodes found")
    node_count: int = Field(..., description="Total nodes in subgraph")
    edge_count: int = Field(..., description="Total edges in subgraph")
    context_length: int = Field(..., description="Context string length in characters")
    query_type: str = Field(default="", description="Classified query type")
    retrieval_strategy: str = Field(default="", description="Retrieval strategy used")
    provenance_score: float | None = Field(None, description="Answer groundedness score (0-1)")
    unsupported_claims: list[str] = Field(
        default_factory=list, description="Claims not supported by context"
    )
    step_timings: dict[str, float | dict[str, float]] = Field(
        default_factory=dict,
        description="Per-step durations in ms. 'retrieve_detail' contains sub-step breakdown.",
    )


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
    traversal_path: list[TraversalStep] = Field(
        default_factory=list, description="Hop-by-hop traversal path explaining how the answer was constructed"
    )
    latency_ms: int = Field(..., description="Total latency in milliseconds")
    metadata: PipelineMetadata | None = Field(
        None, description="Detailed pipeline execution metadata"
    )
