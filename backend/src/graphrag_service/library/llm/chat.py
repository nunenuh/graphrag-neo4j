"""
Chat model wrapper — provides generate function using LangChain chat models.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from graphrag_service.core.logging import get_logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_chat_model

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""


def generate(
    question: str, context: str, system_prompt: str = SYSTEM_PROMPT
) -> str:
    """Generate an answer given a question and context string."""
    try:
        chat = get_chat_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
        ]
        response = chat.invoke(messages)
        return str(response.content)
    except Exception as e:
        raise ServiceException(f"LLM generation failed: {e}") from e
