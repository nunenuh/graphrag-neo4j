"""Tests for evaluation judge module."""

import json
from unittest.mock import MagicMock

from tests.evaluation.judge import JUDGE_PROMPT, judge_answer


class TestJudgeAnswer:
    """Test judge_answer."""

    def _make_chat_model_fn(self, response_text: str):
        mock_response = MagicMock()
        mock_response.content = response_text
        mock_chat = MagicMock()
        mock_chat.invoke.return_value = mock_response
        return lambda: mock_chat

    def test_parses_valid_json(self):
        scores = {
            "relevance": 0.9, "accuracy": 0.8,
            "completeness": 0.7, "groundedness": 0.85, "overall": 0.82,
        }
        chat_fn = self._make_chat_model_fn(json.dumps(scores))
        result = judge_answer(
            question="What is X?",
            answer="X is a method",
            context="X is a deep learning method",
            gold_keywords=["method"],
            chat_model_fn=chat_fn,
        )
        assert result["relevance"] == 0.9
        assert result["accuracy"] == 0.8
        assert result["overall"] == 0.82

    def test_parses_markdown_code_block(self):
        scores = {"relevance": 0.5, "accuracy": 0.5, "completeness": 0.5, "groundedness": 0.5, "overall": 0.5}
        response = f"```json\n{json.dumps(scores)}\n```"
        chat_fn = self._make_chat_model_fn(response)
        result = judge_answer("q", "a", "c", ["k"], chat_fn)
        assert result["relevance"] == 0.5

    def test_clamps_scores_to_01(self):
        scores = {"relevance": 1.5, "accuracy": -0.3, "completeness": 0.5, "groundedness": 0.5, "overall": 0.5}
        chat_fn = self._make_chat_model_fn(json.dumps(scores))
        result = judge_answer("q", "a", "c", ["k"], chat_fn)
        assert result["relevance"] == 1.0
        assert result["accuracy"] == 0.0

    def test_returns_zeros_on_error(self):
        def failing_fn():
            raise RuntimeError("model error")
        result = judge_answer("q", "a", "c", ["k"], failing_fn)
        assert result["overall"] == 0.0
        assert result["relevance"] == 0.0

    def test_judge_prompt_exists(self):
        assert "relevance" in JUDGE_PROMPT
        assert "accuracy" in JUDGE_PROMPT
        assert "completeness" in JUDGE_PROMPT
        assert "groundedness" in JUDGE_PROMPT
