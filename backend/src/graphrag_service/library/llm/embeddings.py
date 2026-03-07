"""
Embedding wrapper — provides embed_text and embed_batch using LangChain embeddings.
"""

from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_embeddings

logger = get_logger(__name__)


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns zero vector for empty input."""
    if not text or not text.strip():
        return [0.0] * get_settings().EMBEDDING_DIM

    try:
        embeddings = get_embeddings()
        return embeddings.embed_query(text.replace("\n", " "))
    except Exception as e:
        raise ServiceException(f"Embedding failed: {e}")


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed a list of texts in batches. Returns embeddings in input order."""
    embeddings_model = get_embeddings()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ") if t else "" for t in texts[i : i + batch_size]]
        try:
            batch_embeddings = embeddings_model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            raise ServiceException(f"Batch embedding failed at index {i}: {e}")

    return all_embeddings
