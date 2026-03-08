"""Unit tests for library/graph/query_classifier.py."""

import json
from unittest.mock import MagicMock

from graphrag_service.library.graph.query_classifier import classify_query


def _mock_chat_model(response_text: str):
    """Create a mock chat model factory returning given text."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_text
    mock_model.invoke.return_value = mock_response

    def factory():
        return mock_model

    return factory


class TestClassifyQuery:
    def test_factual_lookup(self):
        response = json.dumps({
            "query_type": "FACTUAL_LOOKUP",
            "confidence": 0.95,
            "entities": ["YOLO"],
        })
        result = classify_query("What is YOLO?", _mock_chat_model(response))
        assert result["query_type"] == "FACTUAL_LOOKUP"
        assert result["confidence"] == 0.95
        assert "YOLO" in result["entities"]

    def test_comparison(self):
        response = json.dumps({
            "query_type": "COMPARISON",
            "confidence": 0.88,
            "entities": ["BERT", "GPT"],
        })
        result = classify_query("Compare BERT vs GPT", _mock_chat_model(response))
        assert result["query_type"] == "COMPARISON"
        assert len(result["entities"]) == 2

    def test_temporal(self):
        response = json.dumps({
            "query_type": "TEMPORAL",
            "confidence": 0.90,
            "entities": ["ImageNet"],
        })
        result = classify_query("SOTA for ImageNet in 2022?", _mock_chat_model(response))
        assert result["query_type"] == "TEMPORAL"

    def test_network(self):
        response = json.dumps({
            "query_type": "NETWORK",
            "confidence": 0.85,
            "entities": ["Hinton"],
        })
        result = classify_query("Co-authors of Hinton?", _mock_chat_model(response))
        assert result["query_type"] == "NETWORK"

    def test_exploratory(self):
        response = json.dumps({
            "query_type": "EXPLORATORY",
            "confidence": 0.80,
            "entities": ["object detection"],
        })
        result = classify_query(
            "What methods are used for object detection?",
            _mock_chat_model(response),
        )
        assert result["query_type"] == "EXPLORATORY"

    def test_aggregation(self):
        response = json.dumps({
            "query_type": "AGGREGATION",
            "confidence": 0.92,
            "entities": ["transformers"],
        })
        result = classify_query(
            "How many papers use transformers?",
            _mock_chat_model(response),
        )
        assert result["query_type"] == "AGGREGATION"

    def test_multi_hop(self):
        response = json.dumps({
            "query_type": "MULTI_HOP",
            "confidence": 0.75,
            "entities": ["Hinton"],
        })
        result = classify_query(
            "Datasets used by methods in papers by Hinton?",
            _mock_chat_model(response),
        )
        assert result["query_type"] == "MULTI_HOP"

    def test_invalid_type_falls_back(self):
        response = json.dumps({
            "query_type": "INVALID_TYPE",
            "confidence": 0.5,
            "entities": [],
        })
        result = classify_query("Something", _mock_chat_model(response))
        assert result["query_type"] == "EXPLORATORY"

    def test_invalid_json_falls_back(self):
        result = classify_query("Something", _mock_chat_model("not json"))
        assert result["query_type"] == "EXPLORATORY"
        assert result["confidence"] == 0.0

    def test_exception_falls_back(self):
        def bad_factory():
            raise RuntimeError("LLM down")

        result = classify_query("Something", bad_factory)
        assert result["query_type"] == "EXPLORATORY"
        assert result["confidence"] == 0.0

    def test_markdown_code_block(self):
        response = '```json\n{"query_type": "FACTUAL_LOOKUP", "confidence": 0.9, "entities": ["ResNet"]}\n```'
        result = classify_query("What is ResNet?", _mock_chat_model(response))
        assert result["query_type"] == "FACTUAL_LOOKUP"

    def test_lowercase_type_normalized(self):
        response = json.dumps({
            "query_type": "factual_lookup",
            "confidence": 0.9,
            "entities": [],
        })
        result = classify_query("test", _mock_chat_model(response))
        assert result["query_type"] == "FACTUAL_LOOKUP"
