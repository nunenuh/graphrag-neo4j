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
    traversal_depth: int
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
    step_timings: dict[str, Any]


def build_rag_graph(
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list, list]],
    build_context_fn: Callable[..., str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
    classify_fn: Callable[[str], dict] | None = None,
    route_fn: Callable[[str], str] | None = None,
    graph_retrieve_fn: Callable[[str, list[str]], tuple[dict, list]] | None = None,
    merge_fn: Callable | None = None,
    provenance_fn: Callable[[str, str], dict] | None = None,
    enable_provenance: bool = True,
    suggest_depth_fn: Callable[[str], int] | None = None,
    requested_depth: int | None = None,
    bm25_fn: Callable[[str, int], list[dict]] | None = None,
) -> StateGraph:
    """Build the branching RAG pipeline graph with injected functions.

    When classify_fn and route_fn are provided, uses agentic routing.
    Otherwise falls back to the linear VECTOR_ONLY pipeline.

    Args:
        requested_depth: User-requested traversal depth (overrides router suggestion).
        suggest_depth_fn: Function to suggest depth based on query type.
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
                "traversal_depth": requested_depth or 2,
                "entities": [],
                "step_timings": _record_timing(state, "analyze", 0.0),
            }
        t0 = time.perf_counter()
        classification = _timed("analyze", classify_fn, state["question"])
        ms = round((time.perf_counter() - t0) * 1000, 1)
        query_type = classification.get("query_type", "EXPLORATORY")
        strategy = route_fn(query_type) if route_fn else "VECTOR_ONLY"
        # Determine depth: user request > router suggestion > default
        depth = requested_depth
        if depth is None and suggest_depth_fn is not None:
            depth = suggest_depth_fn(query_type)
        if depth is None:
            depth = 2
        return {
            "query_type": query_type,
            "retrieval_strategy": strategy,
            "traversal_depth": depth,
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
        sub_timings: dict[str, float] = {}

        graph_nodes: dict = {}
        graph_edges: list = []
        vector_nodes: dict = {}
        vector_edges: list = []
        bm25_nodes: dict = {}
        traversal_path: list = []

        if strategy in ("GRAPH_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"):
            if graph_retrieve_fn is not None:
                t_sub = time.perf_counter()
                graph_nodes, graph_edges = _timed(
                    "graph_retrieve",
                    graph_retrieve_fn,
                    state.get("query_type", "EXPLORATORY"),
                    state.get("entities", []),
                )
                sub_timings["graph_retrieve"] = round((time.perf_counter() - t_sub) * 1000, 1)

        if strategy in ("VECTOR_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"):
            vector = state.get("query_vector", [])
            if vector:
                t_sub = time.perf_counter()
                results = _timed("vector_search", search_fn, vector, top_k)
                sub_timings["vector_search"] = round((time.perf_counter() - t_sub) * 1000, 1)

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
                    t_sub = time.perf_counter()
                    traverse_depth = state.get("traversal_depth", 2)
                    vector_nodes, vector_edges, traversal_path = _timed("traverse", traverse_fn, ids, traverse_depth)
                    sub_timings["graph_traverse"] = round((time.perf_counter() - t_sub) * 1000, 1)

                # Store seed_nodes for context building
                state_update = {"seed_nodes": seeds}
            else:
                state_update = {"seed_nodes": []}
        else:
            state_update = {"seed_nodes": state.get("seed_nodes", [])}

        # BM25 fulltext search (runs for hybrid strategies when available)
        if bm25_fn is not None and strategy in ("HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"):
            t_sub = time.perf_counter()
            bm25_results = _timed("bm25_search", bm25_fn, state["question"], top_k)
            sub_timings["bm25_search"] = round((time.perf_counter() - t_sub) * 1000, 1)
            for item in bm25_results:
                uid = item.get("uid", "")
                if uid:
                    bm25_nodes[uid] = {
                        "uid": uid,
                        "label": item.get("label", ""),
                        "name": item.get("name", ""),
                        **item.get("properties", {}),
                    }

        # Merge results
        if strategy in ("HYBRID_PARALLEL", "HYBRID_SEQUENTIAL") and merge_fn:
            t_sub = time.perf_counter()
            # Merge vector + graph, then fold in BM25 nodes
            merged_nodes, merged_edges = merge_fn(
                graph_nodes, graph_edges, vector_nodes, vector_edges
            )
            # Add BM25-only nodes that aren't already in merged results
            for uid, node in bm25_nodes.items():
                if uid not in merged_nodes:
                    merged_nodes[uid] = node
            sub_timings["rrf_merge"] = round((time.perf_counter() - t_sub) * 1000, 1)
        elif strategy == "GRAPH_ONLY":
            merged_nodes, merged_edges = graph_nodes, graph_edges
        else:
            merged_nodes, merged_edges = vector_nodes, vector_edges

        ms = round((time.perf_counter() - t0) * 1000, 1)

        # Record both the total retrieve time and sub-step breakdown
        timings = dict(state.get("step_timings") or {})
        timings["retrieve"] = ms
        timings["retrieve_detail"] = sub_timings

        state_update.update({
            "graph_results": {"nodes": graph_nodes, "edges": graph_edges},
            "vector_results": {"nodes": vector_nodes, "edges": vector_edges},
            "merged_results": {"nodes": merged_nodes, "edges": merged_edges},
            "subgraph": {
                "seed_nodes": state_update.get("seed_nodes", state.get("seed_nodes", [])),
                "nodes": list(merged_nodes.values()),
                "edges": merged_edges,
                "cypher_used": f"{strategy} retrieval",
                "traversal_path": traversal_path,
            },
            "step_timings": timings,
        })
        return state_update

    # ── Node: build context ──────────────────────────────────────

    def context_step(state: RAGState) -> dict:
        t0 = time.perf_counter()
        subgraph = state.get("subgraph", {})
        context = _timed(
            "build_context",
            build_context_fn,
            state.get("seed_nodes", []),
            subgraph.get("edges", []),
            subgraph.get("nodes", []),
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
    traverse_fn: Callable[[list[str]], tuple[dict, list, list]],
    build_context_fn: Callable[..., str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
    classify_fn: Callable[[str], dict] | None = None,
    route_fn: Callable[[str], str] | None = None,
    graph_retrieve_fn: Callable[[str, list[str]], tuple[dict, list]] | None = None,
    merge_fn: Callable | None = None,
    provenance_fn: Callable[[str, str], dict] | None = None,
    enable_provenance: bool = True,
    suggest_depth_fn: Callable[[str], int] | None = None,
    requested_depth: int | None = None,
    bm25_fn: Callable[[str, int], list[dict]] | None = None,
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
        suggest_depth_fn=suggest_depth_fn,
        requested_depth=requested_depth,
        bm25_fn=bm25_fn,
    )
    app = graph.compile()
    result = app.invoke({"question": question})
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.bind(total_ms=total_ms).info("rag_pipeline.done")
    return result
