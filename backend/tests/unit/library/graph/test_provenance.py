"""Unit tests for library/graph/provenance.py."""

import json
from unittest.mock import MagicMock

from graphrag_service.library.graph.provenance import validate_provenance


def _mock_chat_model(response_text: str):
    """Create a mock chat model factory returning given text."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_text
    mock_model.invoke.return_value = mock_response

    def factory():
        return mock_model

    return factory


class TestValidateProvenance:
    def test_fully_supported(self):
        response = json.dumps({
            "provenance_score": 1.0,
            "supported_claims": ["ResNet uses residual connections"],
            "unsupported_claims": [],
        })
        result = validate_provenance(
            "ResNet uses residual connections.",
            "ResNet is known for residual connections.",
            _mock_chat_model(response),
        )
        assert result["provenance_score"] == 1.0
        assert result["unsupported_claims"] == []

    def test_partially_supported(self):
        response = json.dumps({
            "provenance_score": 0.5,
            "supported_claims": ["BERT uses transformers"],
            "unsupported_claims": ["BERT was trained on 1TB of data"],
        })
        result = validate_provenance(
            "BERT uses transformers and was trained on 1TB of data.",
            "BERT is a transformer model.",
            _mock_chat_model(response),
        )
        assert result["provenance_score"] == 0.5
        assert len(result["unsupported_claims"]) == 1

    def test_no_support(self):
        response = json.dumps({
            "provenance_score": 0.0,
            "supported_claims": [],
            "unsupported_claims": ["Made up claim"],
        })
        result = validate_provenance(
            "Made up claim.", "Unrelated context.", _mock_chat_model(response)
        )
        assert result["provenance_score"] == 0.0

    def test_score_clamped(self):
        response = json.dumps({
            "provenance_score": 1.5,
            "unsupported_claims": [],
        })
        result = validate_provenance("a", "b", _mock_chat_model(response))
        assert result["provenance_score"] == 1.0

    def test_negative_score_clamped(self):
        response = json.dumps({
            "provenance_score": -0.5,
            "unsupported_claims": [],
        })
        result = validate_provenance("a", "b", _mock_chat_model(response))
        assert result["provenance_score"] == 0.0

    def test_invalid_json_fallback(self):
        result = validate_provenance("a", "b", _mock_chat_model("not json"))
        assert result["provenance_score"] == 0.0
        assert result["unsupported_claims"] == []

    def test_exception_fallback(self):
        def bad_factory():
            raise RuntimeError("LLM down")

        result = validate_provenance("a", "b", bad_factory)
        assert result["provenance_score"] == 0.0

    def test_markdown_code_block(self):
        response = '```json\n{"provenance_score": 0.8, "unsupported_claims": []}\n```'
        result = validate_provenance("a", "b", _mock_chat_model(response))
        assert result["provenance_score"] == 0.8
