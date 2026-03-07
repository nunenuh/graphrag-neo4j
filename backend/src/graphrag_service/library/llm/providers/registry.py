"""
Provider registry — resolves provider name to module and creates model instances.

This is the single entry point for obtaining chat models and embeddings.
Each provider module exposes get_chat_model(settings) and get_embeddings(settings).
"""

from typing import Callable

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings, get_settings

from . import google, ollama, openai, qwen

# Provider name -> module with get_chat_model / get_embeddings
_PROVIDERS: dict[str, object] = {
    "openai": openai,
    "google": google,
    "ollama": ollama,
    "qwen": qwen,
}


def get_chat_model() -> BaseChatModel:
    """Create a chat model instance based on LLM_PROVIDER config."""
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    module = _PROVIDERS.get(provider)
    if module is None:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Available: {', '.join(_PROVIDERS)}"
        )

    return module.get_chat_model(settings)


def get_embeddings() -> Embeddings:
    """Create an embeddings instance based on EMBEDDING_PROVIDER config."""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()

    module = _PROVIDERS.get(provider)
    if module is None:
        raise ValueError(
            f"Unsupported embedding provider: '{provider}'. "
            f"Available: {', '.join(_PROVIDERS)}"
        )

    return module.get_embeddings(settings)
