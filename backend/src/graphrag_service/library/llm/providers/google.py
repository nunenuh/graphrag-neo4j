"""
Google provider — Gemini chat and embeddings via langchain-google-genai.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    """Create a Google Gemini chat model."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


def get_embeddings(settings: Settings) -> Embeddings:
    """Create Google Gemini embeddings."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )
