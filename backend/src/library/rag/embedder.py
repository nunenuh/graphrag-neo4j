from openai import OpenAI
from core.config import settings

_client = OpenAI(api_key=settings.openai_api_key)


def embed_text(text: str) -> list[float]:
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * settings.embedding_dim
    response = _client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    results = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip() for t in texts[i:i + batch_size]]
        response = _client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        results.extend([d.embedding for d in response.data])
    return results
