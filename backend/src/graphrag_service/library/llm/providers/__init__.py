"""
LLM provider registry — one module per provider, resolved by config.

To add a new provider:
1. Create a new module (e.g. providers/anthropic.py)
2. Implement get_chat_model(settings) and get_embeddings(settings)
3. Register it in registry.py _PROVIDERS dict
"""

from .registry import get_chat_model, get_embeddings

__all__ = ["get_chat_model", "get_embeddings"]
