"""Unit tests for library.llm.chat."""

from unittest.mock import MagicMock, patch

import pytest

from graphrag_service.shared.exceptions import ServiceException


class TestGenerate:
    @patch("graphrag_service.library.llm.chat.get_chat_model")
    def test_basic(self, mock_get):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The answer is 42."
        mock_chat.invoke.return_value = mock_response
        mock_get.return_value = mock_chat

        from graphrag_service.library.llm.chat import generate
        result = generate("What?", "Some context")
        assert result == "The answer is 42."

    @patch("graphrag_service.library.llm.chat.get_chat_model")
    def test_passes_system_and_human_messages(self, mock_get):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "answer"
        mock_chat.invoke.return_value = mock_response
        mock_get.return_value = mock_chat

        from graphrag_service.library.llm.chat import generate
        generate("Q", "C")
        messages = mock_chat.invoke.call_args[0][0]
        assert len(messages) == 2
        assert "Context" in messages[1].content
        assert "Q" in messages[1].content

    @patch("graphrag_service.library.llm.chat.get_chat_model")
    def test_custom_system_prompt(self, mock_get):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "custom"
        mock_chat.invoke.return_value = mock_response
        mock_get.return_value = mock_chat

        from graphrag_service.library.llm.chat import generate
        generate("Q", "C", system_prompt="You are a pirate.")
        messages = mock_chat.invoke.call_args[0][0]
        assert messages[0].content == "You are a pirate."

    @patch("graphrag_service.library.llm.chat.get_chat_model")
    def test_raises_service_exception(self, mock_get):
        mock_chat = MagicMock()
        mock_chat.invoke.side_effect = Exception("LLM down")
        mock_get.return_value = mock_chat

        from graphrag_service.library.llm.chat import generate
        with pytest.raises(ServiceException, match="LLM generation failed"):
            generate("Q", "C")
