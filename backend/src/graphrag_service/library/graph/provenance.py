"""Post-synthesis provenance validation.

Uses LLM-as-judge to check factual claims in answers against context.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger


PROVENANCE_PROMPT = """You are a factual accuracy checker. Given an answer and its source context,
check whether each factual claim in the answer is supported by the context.

Respond with ONLY a JSON object:
{
    "provenance_score": <0.0 to 1.0>,
    "supported_claims": ["claim 1", "claim 2"],
    "unsupported_claims": ["claim X"]
}

Rules:
- provenance_score = supported_claims / total_claims (or 1.0 if no claims)
- A claim is "supported" if the context contains evidence for it
- A claim is "unsupported" if the context does NOT contain evidence
- Be strict: vague or general statements without specific context support are unsupported"""


def validate_provenance(
    answer: str,
    context: str,
    chat_model_fn: callable,
) -> dict:
    """Validate answer provenance against context using LLM-as-judge.

    Args:
        answer: The generated answer to validate.
        context: The context used for generation.
        chat_model_fn: Callable that returns a LangChain chat model.

    Returns:
        Dict with keys: provenance_score (float), unsupported_claims (list[str]).
    """
    try:
        chat = chat_model_fn()
        messages = [
            SystemMessage(content=PROVENANCE_PROMPT),
            HumanMessage(
                content=f"Context:\n{context}\n\nAnswer:\n{answer}"
            ),
        ]
        response = chat.invoke(messages)
        raw = str(response.content).strip()

        # Parse JSON from response
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        score = float(parsed.get("provenance_score", 0.0))
        unsupported = parsed.get("unsupported_claims", [])

        result = {
            "provenance_score": round(min(max(score, 0.0), 1.0), 4),
            "unsupported_claims": unsupported if isinstance(unsupported, list) else [],
        }
        logger.bind(
            provenance_score=result["provenance_score"],
            unsupported_count=len(result["unsupported_claims"]),
        ).info("provenance.result")
        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.bind(error=str(e)).warning("provenance.parse_failed")
        return {"provenance_score": 0.0, "unsupported_claims": []}
    except Exception as e:
        logger.bind(error=str(e)).error("provenance.failed")
        return {"provenance_score": 0.0, "unsupported_claims": []}
