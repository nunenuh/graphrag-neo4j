"""
Chat model wrapper — provides generate function using LangChain chat models.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from loguru import logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_chat_model


SYSTEM_PROMPT = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""


def generate(
    question: str, context: str, system_prompt: str = SYSTEM_PROMPT
) -> str:
    """Generate an answer given a question and context string."""
    try:
        chat = get_chat_model()
        logger.bind(question_len=len(question), context_len=len(context)).debug("llm.generate.start")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
        ]
        response = chat.invoke(messages)
        answer = str(response.content)
        logger.bind(answer_len=len(answer)).debug("llm.generate.done")
        return answer
    except Exception as e:
        logger.bind(error=str(e)).error("llm.generate.failed")
        raise ServiceException(f"LLM generation failed: {e}") from e
