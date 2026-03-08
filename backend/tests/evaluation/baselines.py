"""Baseline system implementations for ablation study."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class BaselineConfig:
    """Configuration for a baseline system."""

    name: str
    description: str
    use_vector_search: bool = True
    use_graph_retrieval: bool = False
    use_classification: bool = False
    use_provenance: bool = False


BASELINE_CONFIGS = {
    "llm_only": BaselineConfig(
        name="LLM-only",
        description="Direct LLM call with question only, no retrieval",
        use_vector_search=False,
        use_graph_retrieval=False,
        use_classification=False,
        use_provenance=False,
    ),
    "plain_rag": BaselineConfig(
        name="Plain RAG",
        description="Vector search only, no graph traversal routing",
        use_vector_search=True,
        use_graph_retrieval=False,
        use_classification=False,
        use_provenance=False,
    ),
    "graph_only": BaselineConfig(
        name="Graph-only",
        description="Cypher query only, no vector search",
        use_vector_search=False,
        use_graph_retrieval=True,
        use_classification=False,
        use_provenance=False,
    ),
    "hybrid_full": BaselineConfig(
        name="Hybrid (full pipeline)",
        description="Full agentic pipeline with classification, routing, and provenance",
        use_vector_search=True,
        use_graph_retrieval=True,
        use_classification=True,
        use_provenance=True,
    ),
}


def build_pipeline_kwargs(
    config: BaselineConfig,
    embed_fn: Callable,
    search_fn: Callable,
    traverse_fn: Callable,
    build_context_fn: Callable,
    generate_fn: Callable,
    top_k: int = 5,
    classify_fn: Callable | None = None,
    route_fn: Callable | None = None,
    graph_retrieve_fn: Callable | None = None,
    merge_fn: Callable | None = None,
    provenance_fn: Callable | None = None,
) -> dict[str, Any]:
    """Build pipeline kwargs based on baseline configuration.

    Returns kwargs dict for run_rag_pipeline().
    """
    kwargs: dict[str, Any] = {
        "embed_fn": embed_fn,
        "search_fn": search_fn,
        "traverse_fn": traverse_fn,
        "build_context_fn": build_context_fn,
        "generate_fn": generate_fn,
        "top_k": top_k,
    }

    if config.use_classification and classify_fn:
        kwargs["classify_fn"] = classify_fn
        kwargs["route_fn"] = route_fn

    if config.use_graph_retrieval and graph_retrieve_fn:
        kwargs["graph_retrieve_fn"] = graph_retrieve_fn
        kwargs["merge_fn"] = merge_fn

    kwargs["provenance_fn"] = provenance_fn if config.use_provenance else None
    kwargs["enable_provenance"] = config.use_provenance

    return kwargs


def get_baseline_configs() -> dict[str, BaselineConfig]:
    """Return all baseline configurations."""
    return dict(BASELINE_CONFIGS)
