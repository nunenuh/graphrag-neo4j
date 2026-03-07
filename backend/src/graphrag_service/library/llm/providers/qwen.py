"""
Qwen provider — Alibaba Qwen models via OpenAI-compatible API.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings

def get_chat_model(settings: Settings) -> BaseChatModel:
    """Create a Qwen chat model via OpenAI-compatible API."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
    )


def get_embeddings(settings: Settings) -> Embeddings:
    """Create Qwen embeddings via OpenAI-compatible API."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
        check_embedding_ctx_length=False,
    )
