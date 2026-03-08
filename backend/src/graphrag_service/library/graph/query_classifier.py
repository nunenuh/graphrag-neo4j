"""LLM-based query classification into 7 query types.

Classifies user questions to determine optimal retrieval strategy.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from graphrag_service.shared.exceptions import ServiceException

from .router import DEFAULT_QUERY_TYPE, VALID_QUERY_TYPES

CLASSIFICATION_PROMPT = """You are a query classifier for an ML research knowledge graph.
Classify the user's question into exactly ONE of these query types:

1. FACTUAL_LOOKUP — Direct facts about a single entity (e.g. "What is YOLO?", "Describe ResNet")
2. COMPARISON — Comparing two or more entities (e.g. "Compare BERT vs GPT", "Differences between CNN and RNN")
3. TEMPORAL — Time-based queries, trends over years (e.g. "SOTA for ImageNet in 2022?", "Methods before 2020")
4. NETWORK — Relationship/collaboration queries (e.g. "Bridge authors between NLP and CV", "Co-authors of Hinton")
5. EXPLORATORY — Open-ended exploration (e.g. "What methods are used for object detection?", "Popular datasets for NLP")
6. AGGREGATION — Counting or summarizing (e.g. "How many papers use transformers?", "Most common tasks")
7. MULTI_HOP — Requires chaining multiple relationships (e.g. "Datasets used by methods in papers by Hinton?")

Respond with ONLY a JSON object, no other text:
{"query_type": "<TYPE>", "confidence": <0.0-1.0>, "entities": ["<extracted entities>"]}

If unsure, default to EXPLORATORY."""


def classify_query(
    question: str,
    chat_model_fn: callable,
) -> dict:
    """Classify a question into a query type using LLM.

    Args:
        question: The user's question.
        chat_model_fn: Callable that returns a LangChain chat model.

    Returns:
        Dict with keys: query_type, confidence, entities.
    """
    try:
        chat = chat_model_fn()
        messages = [
            SystemMessage(content=CLASSIFICATION_PROMPT),
            HumanMessage(content=question),
        ]
        response = chat.invoke(messages)
        raw = str(response.content).strip()

        # Parse JSON from response (handle markdown code blocks)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        query_type = parsed.get("query_type", DEFAULT_QUERY_TYPE).upper()

        if query_type not in VALID_QUERY_TYPES:
            logger.bind(raw_type=query_type).warning("classifier.invalid_type")
            query_type = DEFAULT_QUERY_TYPE

        result = {
            "query_type": query_type,
            "confidence": float(parsed.get("confidence", 0.5)),
            "entities": parsed.get("entities", []),
        }
        logger.bind(**result).info("classifier.result")
        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.bind(error=str(e)).warning("classifier.parse_failed")
        return {
            "query_type": DEFAULT_QUERY_TYPE,
            "confidence": 0.0,
            "entities": [],
        }
    except Exception as e:
        logger.bind(error=str(e)).error("classifier.failed")
        return {
            "query_type": DEFAULT_QUERY_TYPE,
            "confidence": 0.0,
            "entities": [],
        }
