"""Unit tests for RAG module usecase."""

from unittest.mock import MagicMock, patch

from graphrag_service.modules.rag.usecase import RAGUseCase


class TestRAGUseCase:
    @patch("graphrag_service.modules.rag.usecase.run_rag_pipeline")
    def test_query_delegates_to_pipeline(self, mock_pipeline, mock_neo4j_client):
        mock_pipeline.return_value = {
            "question": "What is ResNet?",
            "answer": "ResNet is...",
            "subgraph": {"seed_nodes": [], "nodes": [], "edges": [], "cypher_used": ""},
        }
        uc = RAGUseCase(mock_neo4j_client)
        result = uc.query("What is ResNet?")

        assert result["answer"] == "ResNet is..."
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["question"] == "What is ResNet?"

    @patch("graphrag_service.modules.rag.usecase.run_rag_pipeline")
    def test_query_passes_correct_functions(self, mock_pipeline, mock_neo4j_client):
        mock_pipeline.return_value = {"answer": "test"}
        uc = RAGUseCase(mock_neo4j_client)
        uc.query("test")

        call_kwargs = mock_pipeline.call_args[1]
        assert callable(call_kwargs["embed_fn"])
        assert callable(call_kwargs["search_fn"])
        assert callable(call_kwargs["traverse_fn"])
        assert callable(call_kwargs["build_context_fn"])
        assert callable(call_kwargs["generate_fn"])
