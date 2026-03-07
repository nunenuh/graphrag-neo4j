"""LangChain-based LLM abstraction — provider-agnostic chat and embeddings."""

from .chat import SYSTEM_PROMPT, generate
from .embeddings import embed_batch, embed_text
from .providers import get_chat_model, get_embeddings

__all__ = [
    "get_chat_model",
    "get_embeddings",
    "embed_text",
    "embed_batch",
    "generate",
    "SYSTEM_PROMPT",
]
