"""Unit tests for core.dependencies."""

from unittest.mock import MagicMock, patch

from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client


class TestNeo4jClientDependency:
    def setup_method(self):
        import graphrag_service.core.dependencies as deps
        deps._neo4j_client = None

    @patch("graphrag_service.core.dependencies.Neo4jClient")
    def test_get_creates_singleton(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        c1 = get_neo4j_client()
        c2 = get_neo4j_client()
        assert c1 is c2
        MockClient.assert_called_once()

    @patch("graphrag_service.core.dependencies.Neo4jClient")
    def test_close_calls_client_close(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        get_neo4j_client()
        close_neo4j_client()
        mock_instance.close.assert_called_once()

    @patch("graphrag_service.core.dependencies.Neo4jClient")
    def test_close_resets_singleton(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        get_neo4j_client()
        close_neo4j_client()

        import graphrag_service.core.dependencies as deps
        assert deps._neo4j_client is None

    def test_close_noop_when_no_client(self):
        close_neo4j_client()  # should not raise

    def teardown_method(self):
        import graphrag_service.core.dependencies as deps
        deps._neo4j_client = None
