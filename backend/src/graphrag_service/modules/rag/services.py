"""
RAG service — orchestrates library calls for embedding, context building, and generation.

Does NOT access the database. Uses library/ for reusable logic.
"""

from loguru import logger

from graphrag_service.library.generator import build_context
from graphrag_service.library.llm import embed_text, generate


class RAGService:
    """Orchestrates LLM library calls for the RAG pipeline. No DB access."""

    @staticmethod
    def embed_question(question: str) -> list[float]:
        """Embed a question using library/llm."""
        return embed_text(question)

    @staticmethod
    def generate_answer(question: str, context: str) -> str:
        """Generate an answer using library/llm."""
        return generate(question, context)

    @staticmethod
    def build_context(seed_nodes: list, edges: list, nodes: list | None = None) -> str:
        """Build context string using library/generator."""
        return build_context(seed_nodes, edges, nodes)
