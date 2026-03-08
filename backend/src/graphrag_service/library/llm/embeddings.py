"""
Embedding wrapper — provides embed_text and embed_batch using LangChain embeddings.
"""

from graphrag_service.core.config import get_settings
from loguru import logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_embeddings



def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns zero vector for empty input."""
    if not text or not text.strip():
        logger.debug("embed.skip_empty")
        return [0.0] * get_settings().EMBEDDING_DIM

    try:
        embeddings = get_embeddings()
        result = embeddings.embed_query(text.replace("\n", " "))
        logger.bind(text_len=len(text), dim=len(result)).debug("embed.done")
        return result
    except Exception as e:
        logger.bind(text_len=len(text), error=str(e)).error("embed.failed")
        raise ServiceException(f"Embedding failed: {e}") from e


def embed_batch(texts: list[str], batch_size: int = 6) -> list[list[float]]:
    """Embed a list of texts in batches. Returns embeddings in input order.

    Default batch_size=6 is conservative for DashScope (max 10 texts, 8192 tokens/batch).
    """
    embeddings_model = get_embeddings()
    all_embeddings: list[list[float]] = []
    dim = get_settings().EMBEDDING_DIM

    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ") if t and t.strip() else "empty" for t in texts[i : i + batch_size]]
        try:
            batch_embeddings = embeddings_model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.warning(f"Batch embedding failed at index {i}, falling back to zero vectors: {e}")
            all_embeddings.extend([[0.0] * dim] * len(batch))

    return all_embeddings
