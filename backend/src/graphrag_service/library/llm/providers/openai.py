"""
OpenAI provider — ChatGPT and OpenAI embeddings via langchain-openai.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    """Create an OpenAI chat model."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
    )


def get_embeddings(settings: Settings) -> Embeddings:
    """Create OpenAI embeddings."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
        dimensions=settings.EMBEDDING_DIM,
    )
