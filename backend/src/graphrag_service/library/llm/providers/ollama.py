"""
Ollama provider — local models via langchain-ollama.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    """Create an Ollama chat model."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def get_embeddings(settings: Settings) -> Embeddings:
    """Create Ollama embeddings."""
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
