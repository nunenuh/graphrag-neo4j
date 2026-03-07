"""
RAG pipeline as a LangGraph StateGraph.

Functions are injected by the caller (usecase layer), keeping this graph
definition free of DB or provider dependencies.
"""

from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)


class RAGState(TypedDict):
    """State flowing through the RAG pipeline."""

    question: str
    query_vector: list[float]
    seed_nodes: list[dict]
    subgraph: dict
    context: str
    answer: str


def build_rag_graph(
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
) -> StateGraph:
    """Build the RAG pipeline graph with injected functions."""

    def embed_step(state: RAGState) -> dict:
        vector = embed_fn(state["question"])
        return {"query_vector": vector}

    def search_step(state: RAGState) -> dict:
        results = search_fn(state["query_vector"], top_k)
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
        return {"seed_nodes": seeds}

    def traverse_step(state: RAGState) -> dict:
        ids = [s["id"] for s in state["seed_nodes"]]
        nodes_dict, edges_list = traverse_fn(ids)
        return {
            "subgraph": {
                "seed_nodes": state["seed_nodes"],
                "nodes": list(nodes_dict.values()),
                "edges": edges_list,
                "cypher_used": "neomodel VectorFilter + 2-hop traversal",
            }
        }

    def context_step(state: RAGState) -> dict:
        context = build_context_fn(
            state["seed_nodes"],
            state["subgraph"].get("edges", []),
        )
        return {"context": context}

    def generate_step(state: RAGState) -> dict:
        answer = generate_fn(state["question"], state["context"])
        return {"answer": answer}

    graph = StateGraph(RAGState)
    graph.add_node("embed", embed_step)
    graph.add_node("search", search_step)
    graph.add_node("traverse", traverse_step)
    graph.add_node("context", context_step)
    graph.add_node("generate", generate_step)

    graph.set_entry_point("embed")
    graph.add_edge("embed", "search")
    graph.add_edge("search", "traverse")
    graph.add_edge("traverse", "context")
    graph.add_edge("context", "generate")
    graph.add_edge("generate", END)

    return graph


def run_rag_pipeline(
    question: str,
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
) -> RAGState:
    """Build and run the RAG pipeline, returning the final state."""
    graph = build_rag_graph(
        embed_fn, search_fn, traverse_fn, build_context_fn, generate_fn, top_k
    )
    app = graph.compile()
    result = app.invoke({"question": question})
    return result
