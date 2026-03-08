"""
RAG pipeline as a LangGraph StateGraph.

Branching agentic pipeline with query classification, retrieval routing,
hybrid search, and provenance validation.

Functions are injected by the caller (usecase layer), keeping this graph
definition free of DB or provider dependencies.
"""

import time
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from loguru import logger


def _timed(step_name: str, fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """Execute fn with timing and structured logging."""
    logger.bind(step=step_name).info("rag_step.start")
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    duration_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.bind(step=step_name, duration_ms=duration_ms).info("rag_step.done")
    return result


class RAGState(TypedDict):
    """State flowing through the RAG pipeline."""

    question: str
    query_type: str
    retrieval_strategy: str
    entities: list[str]
    query_vector: list[float]
    seed_nodes: list[dict]
    graph_results: dict
    vector_results: dict
    merged_results: dict
    subgraph: dict
    context: str
    answer: str
    provenance_score: float
    unsupported_claims: list[str]
    step_timings: dict[str, float]


def build_rag_graph(
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
    classify_fn: Callable[[str], dict] | None = None,
    route_fn: Callable[[str], str] | None = None,
    graph_retrieve_fn: Callable[[str, list[str]], tuple[dict, list]] | None = None,
    merge_fn: Callable | None = None,
    provenance_fn: Callable[[str, str], dict] | None = None,
    enable_provenance: bool = True,
) -> StateGraph:
    """Build the branching RAG pipeline graph with injected functions.

    When classify_fn and route_fn are provided, uses agentic routing.
    Otherwise falls back to the linear VECTOR_ONLY pipeline.
    """

    def _record_timing(state: RAGState, step: str, duration_ms: float) -> dict:
        """Merge a step timing into the accumulated timings dict."""
        existing = dict(state.get("step_timings") or {})
        existing[step] = duration_ms
        return existing

    # ── Node: analyze query ──────────────────────────────────────

    def analyze_step(state: RAGState) -> dict:
        if classify_fn is None:
            return {
                "query_type": "EXPLORATORY",
                "retrieval_strategy": "VECTOR_ONLY",
                "entities": [],
                "step_timings": _record_timing(state, "analyze", 0.0),
            }
        t0 = time.perf_counter()
        classification = _timed("analyze", classify_fn, state["question"])
        ms = round((time.perf_counter() - t0) * 1000, 1)
        query_type = classification.get("query_type", "EXPLORATORY")
        strategy = route_fn(query_type) if route_fn else "VECTOR_ONLY"
        return {
            "query_type": query_type,
            "retrieval_strategy": strategy,
            "entities": classification.get("entities", []),
            "step_timings": _record_timing(state, "analyze", ms),
        }

    # ── Node: embed ──────────────────────────────────────────────

    def embed_step(state: RAGState) -> dict:
        strategy = state.get("retrieval_strategy", "VECTOR_ONLY")
        # Skip embedding for GRAPH_ONLY (no vector search needed)
        if strategy == "GRAPH_ONLY":
            return {
                "query_vector": [],
                "step_timings": _record_timing(state, "embed", 0.0),
            }
        t0 = time.perf_counter()
        vector = _timed("embed", embed_fn, state["question"])
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"query_vector": vector, "step_timings": _record_timing(state, "embed", ms)}

    # ── Node: retrieve (unified) ─────────────────────────────────

    def retrieve_step(state: RAGState) -> dict:
        strategy = state.get("retrieval_strategy", "VECTOR_ONLY")
        t0 = time.perf_counter()

        graph_nodes: dict = {}
        graph_edges: list = []
        vector_nodes: dict = {}
        vector_edges: list = []

        if strategy in ("GRAPH_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"):
            if graph_retrieve_fn is not None:
                graph_nodes, graph_edges = _timed(
                    "graph_retrieve",
                    graph_retrieve_fn,
                    state.get("query_type", "EXPLORATORY"),
                    state.get("entities", []),
                )

        if strategy in ("VECTOR_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"):
            vector = state.get("query_vector", [])
            if vector:
                results = _timed("vector_search", search_fn, vector, top_k)
                seeds = [
                    {
                        "id": r.id,
                        "label": r.label,
                        "name": r.name,
                        "score": r.score,
                        "properties": r.properties,
                    }
                    for r in results
                ]
                logger.bind(
                    count=len(seeds),
                    top_scores=[s["score"] for s in seeds[:3]],
                ).info("vector_search.results")

                # Traverse from seed nodes
                if seeds:
                    ids = [s["id"] for s in seeds]
                    vector_nodes, vector_edges = _timed("traverse", traverse_fn, ids)

                # Store seed_nodes for context building
                state_update = {"seed_nodes": seeds}
            else:
                state_update = {"seed_nodes": []}
        else:
            state_update = {"seed_nodes": state.get("seed_nodes", [])}

        ms = round((time.perf_counter() - t0) * 1000, 1)

        # Merge results
        if strategy in ("HYBRID_PARALLEL", "HYBRID_SEQUENTIAL") and merge_fn:
            merged_nodes, merged_edges = merge_fn(
                graph_nodes, graph_edges, vector_nodes, vector_edges
            )
        elif strategy == "GRAPH_ONLY":
            merged_nodes, merged_edges = graph_nodes, graph_edges
        else:
            merged_nodes, merged_edges = vector_nodes, vector_edges

        state_update.update({
            "graph_results": {"nodes": graph_nodes, "edges": graph_edges},
            "vector_results": {"nodes": vector_nodes, "edges": vector_edges},
            "merged_results": {"nodes": merged_nodes, "edges": merged_edges},
            "subgraph": {
                "seed_nodes": state_update.get("seed_nodes", state.get("seed_nodes", [])),
                "nodes": list(merged_nodes.values()),
                "edges": merged_edges,
                "cypher_used": f"{strategy} retrieval",
            },
            "step_timings": _record_timing(state, "retrieve", ms),
        })
        return state_update

    # ── Node: build context ──────────────────────────────────────

    def context_step(state: RAGState) -> dict:
        t0 = time.perf_counter()
        context = _timed(
            "build_context",
            build_context_fn,
            state.get("seed_nodes", []),
            state.get("subgraph", {}).get("edges", []),
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.bind(context_len=len(context)).info("build_context.results")
        return {"context": context, "step_timings": _record_timing(state, "build_context", ms)}

    # ── Node: generate answer ────────────────────────────────────

    def generate_step(state: RAGState) -> dict:
        t0 = time.perf_counter()
        answer = _timed("generate", generate_fn, state["question"], state["context"])
        ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.bind(answer_len=len(answer)).info("generate.results")
        return {"answer": answer, "step_timings": _record_timing(state, "generate", ms)}

    # ── Node: validate provenance ────────────────────────────────

    def validate_step(state: RAGState) -> dict:
        if not enable_provenance or provenance_fn is None:
            return {
                "provenance_score": 1.0,
                "unsupported_claims": [],
                "step_timings": _record_timing(state, "validate", 0.0),
            }
        t0 = time.perf_counter()
        result = _timed(
            "validate", provenance_fn, state["answer"], state["context"]
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "provenance_score": result.get("provenance_score", 0.0),
            "unsupported_claims": result.get("unsupported_claims", []),
            "step_timings": _record_timing(state, "validate", ms),
        }

    # ── Build graph ──────────────────────────────────────────────

    graph = StateGraph(RAGState)
    graph.add_node("analyze", analyze_step)
    graph.add_node("embed", embed_step)
    graph.add_node("retrieve", retrieve_step)
    graph.add_node("context", context_step)
    graph.add_node("generate", generate_step)
    graph.add_node("validate", validate_step)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "embed")
    graph.add_edge("embed", "retrieve")
    graph.add_edge("retrieve", "context")
    graph.add_edge("context", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)

    return graph


def run_rag_pipeline(
    question: str,
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
    classify_fn: Callable[[str], dict] | None = None,
    route_fn: Callable[[str], str] | None = None,
    graph_retrieve_fn: Callable[[str, list[str]], tuple[dict, list]] | None = None,
    merge_fn: Callable | None = None,
    provenance_fn: Callable[[str, str], dict] | None = None,
    enable_provenance: bool = True,
) -> RAGState:
    """Build and run the RAG pipeline, returning the final state."""
    logger.bind(question=question[:100], top_k=top_k).info("rag_pipeline.start")
    t0 = time.perf_counter()
    graph = build_rag_graph(
        embed_fn=embed_fn,
        search_fn=search_fn,
        traverse_fn=traverse_fn,
        build_context_fn=build_context_fn,
        generate_fn=generate_fn,
        top_k=top_k,
        classify_fn=classify_fn,
        route_fn=route_fn,
        graph_retrieve_fn=graph_retrieve_fn,
        merge_fn=merge_fn,
        provenance_fn=provenance_fn,
        enable_provenance=enable_provenance,
    )
    app = graph.compile()
    result = app.invoke({"question": question})
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.bind(total_ms=total_ms).info("rag_pipeline.done")
    return result
