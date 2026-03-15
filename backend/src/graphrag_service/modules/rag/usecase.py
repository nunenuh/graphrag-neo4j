"""
RAG use case orchestration layer.

Coordinates service (library calls) + repository (DB) via LangGraph pipeline.
"""

from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.library.graph import run_rag_pipeline
from graphrag_service.library.graph.context_budget import ContextBudget, allocate_context
from graphrag_service.library.graph.graph_retriever import graph_retrieve
from graphrag_service.library.graph.hybrid_retriever import merge_nodes_rrf
from graphrag_service.library.graph.provenance import validate_provenance
from graphrag_service.library.graph.query_classifier import classify_query
from graphrag_service.library.graph.bm25_search import bm25_search
from graphrag_service.library.graph.router import route_query, suggest_depth, clamp_depth
from graphrag_service.library.llm.providers import get_chat_model

from .repositories import TraversalRepository, VectorSearchRepository
from .services import RAGService


class RAGUseCase:
    """Orchestrates the full RAG pipeline — wires service + repository into LangGraph."""

    def __init__(self, client: Neo4jClient):
        self.client = client
        self.service = RAGService()
        self.vector_repo = VectorSearchRepository(client)
        self.traversal_repo = TraversalRepository(client)

    def query(self, question: str, depth: int | None = None) -> dict:
        """Run the RAG pipeline using LangGraph.

        Args:
            question: Natural language question.
            depth: Optional traversal depth override (1-4). If None, router suggests.

        Returns the full pipeline state dict.
        """
        settings = get_settings()

        # Build context function with budget management
        budget = ContextBudget(
            total_tokens=settings.CONTEXT_BUDGET_TOKENS,
            graph_pct=settings.GRAPH_CONTEXT_PCT,
            text_pct=settings.TEXT_CONTEXT_PCT,
            summary_pct=settings.SUMMARY_CONTEXT_PCT,
        )

        def _build_context(seed_nodes: list, edges: list, nodes: list | None = None) -> str:
            return allocate_context(seed_nodes, edges, budget, nodes)

        def _classify(question: str) -> dict:
            return classify_query(question, get_chat_model)

        def _graph_retrieve(query_type: str, entities: list[str]) -> tuple[dict, list]:
            return graph_retrieve(query_type, entities, self.client.run_query)

        def _provenance(answer: str, context: str) -> dict:
            return validate_provenance(answer, context, get_chat_model)

        def _bm25(query: str, top_k: int) -> list[dict]:
            return bm25_search(query, self.client.run_query, top_k)

        result = run_rag_pipeline(
            question=question,
            embed_fn=self.service.embed_question,
            search_fn=self.vector_repo.search_all,
            traverse_fn=self.traversal_repo.traverse,
            build_context_fn=_build_context,
            generate_fn=self.service.generate_answer,
            top_k=settings.TOP_K_SEED_NODES,
            classify_fn=_classify,
            route_fn=route_query,
            graph_retrieve_fn=_graph_retrieve,
            merge_fn=merge_nodes_rrf,
            provenance_fn=_provenance,
            enable_provenance=settings.ENABLE_PROVENANCE,
            suggest_depth_fn=suggest_depth,
            requested_depth=clamp_depth(depth) if depth is not None else None,
            bm25_fn=_bm25,
        )
        return result
