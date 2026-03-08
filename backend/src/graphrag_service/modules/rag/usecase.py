"""
RAG use case orchestration layer.

Coordinates service (library calls) + repository (DB) via LangGraph pipeline.
"""

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.library.graph import run_rag_pipeline

from .repositories import TraversalRepository, VectorSearchRepository
from .services import RAGService


class RAGUseCase:
    """Orchestrates the full RAG pipeline — wires service + repository into LangGraph."""

    def __init__(self, client: Neo4jClient):
        self.service = RAGService()
        self.vector_repo = VectorSearchRepository(client)
        self.traversal_repo = TraversalRepository(client)

    def query(self, question: str) -> dict:
        """Run the RAG pipeline using LangGraph.

        Returns the full pipeline state dict with keys:
            question, query_vector, seed_nodes, subgraph, context, answer
        """
        settings = get_settings()
        result = run_rag_pipeline(
            question=question,
            embed_fn=self.service.embed_question,
            search_fn=self.vector_repo.search_all,
            traverse_fn=self.traversal_repo.traverse,
            build_context_fn=self.service.build_context,
            generate_fn=self.service.generate_answer,
            top_k=settings.TOP_K_SEED_NODES,
        )
        return result
