"""Unit tests for library.llm.embeddings."""

from unittest.mock import MagicMock, patch

import pytest

from graphrag_service.shared.exceptions import ServiceException


class TestEmbedText:
    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_basic(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_text
        result = embed_text("hello")
        assert result == [0.1, 0.2, 0.3]
        mock_model.embed_query.assert_called_once_with("hello")

    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_replaces_newlines(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1]
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_text
        embed_text("hello\nworld")
        mock_model.embed_query.assert_called_once_with("hello world")

    def test_empty_returns_zero_vector(self, settings):
        from graphrag_service.library.llm.embeddings import embed_text
        result = embed_text("")
        assert len(result) == settings.EMBEDDING_DIM
        assert all(v == 0.0 for v in result)

    def test_whitespace_returns_zero_vector(self, settings):
        from graphrag_service.library.llm.embeddings import embed_text
        result = embed_text("   ")
        assert all(v == 0.0 for v in result)

    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_raises_service_exception(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_query.side_effect = Exception("API error")
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_text
        with pytest.raises(ServiceException, match="Embedding failed"):
            embed_text("test")


class TestEmbedBatch:
    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_basic(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_documents.return_value = [[0.1], [0.2]]
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_batch
        result = embed_batch(["a", "b"], batch_size=10)
        assert result == [[0.1], [0.2]]

    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_batching(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_documents.side_effect = [[[0.1], [0.2]], [[0.3]]]
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_batch
        result = embed_batch(["a", "b", "c"], batch_size=2)
        assert len(result) == 3
        assert mock_model.embed_documents.call_count == 2

    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_fallback_on_error(self, mock_get, settings):
        mock_model = MagicMock()
        mock_model.embed_documents.side_effect = Exception("fail")
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_batch
        result = embed_batch(["a", "b"], batch_size=10)
        assert len(result) == 2
        assert all(v == 0.0 for v in result[0])

    @patch("graphrag_service.library.llm.embeddings.get_embeddings")
    def test_empty_strings_replaced(self, mock_get):
        mock_model = MagicMock()
        mock_model.embed_documents.return_value = [[0.1], [0.2]]
        mock_get.return_value = mock_model

        from graphrag_service.library.llm.embeddings import embed_batch
        embed_batch(["hello", ""], batch_size=10)
        call_args = mock_model.embed_documents.call_args[0][0]
        assert call_args[1] == "empty"
