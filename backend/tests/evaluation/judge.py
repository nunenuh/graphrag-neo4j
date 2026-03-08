"""LLM-based answer correctness judge."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger


JUDGE_PROMPT = """You are an answer quality evaluator for an ML research Q&A system.
Given a question, the system's answer, the retrieval context, and expected keywords,
score the answer on 4 dimensions (each 0.0 to 1.0):

1. **relevance**: Does the answer address the question?
2. **accuracy**: Are the facts correct based on the context?
3. **completeness**: Are expected keywords/entities mentioned?
4. **groundedness**: Are claims supported by the retrieved context?

Respond with ONLY a JSON object:
{"relevance": 0.0-1.0, "accuracy": 0.0-1.0, "completeness": 0.0-1.0, "groundedness": 0.0-1.0, "overall": 0.0-1.0}

The "overall" score should be a weighted average: relevance*0.2 + accuracy*0.3 + completeness*0.2 + groundedness*0.3"""


def judge_answer(
    question: str,
    answer: str,
    context: str,
    gold_keywords: list[str],
    chat_model_fn: callable,
) -> dict[str, float]:
    """Judge answer quality using LLM.

    Args:
        question: The original question.
        answer: Generated answer.
        context: Retrieved context used for generation.
        gold_keywords: Expected keywords in correct answer.
        chat_model_fn: Callable returning a LangChain chat model.

    Returns:
        Dict with scores: relevance, accuracy, completeness, groundedness, overall.
    """
    try:
        chat = chat_model_fn()
        user_content = (
            f"Question: {question}\n\n"
            f"Answer: {answer}\n\n"
            f"Context: {context[:2000]}\n\n"
            f"Expected keywords: {', '.join(gold_keywords)}"
        )
        messages = [
            SystemMessage(content=JUDGE_PROMPT),
            HumanMessage(content=user_content),
        ]
        response = chat.invoke(messages)
        raw = str(response.content).strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        scores = {}
        for key in ("relevance", "accuracy", "completeness", "groundedness", "overall"):
            val = float(parsed.get(key, 0.0))
            scores[key] = round(min(max(val, 0.0), 1.0), 4)

        logger.bind(**scores).info("judge.scores")
        return scores

    except Exception as e:
        logger.bind(error=str(e)).warning("judge.failed")
        return {
            "relevance": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "groundedness": 0.0,
            "overall": 0.0,
        }
