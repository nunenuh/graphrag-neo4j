"""Unit tests for health module services."""

from unittest.mock import MagicMock, patch

from graphrag_service.modules.health.services import HealthService


class TestHealthService:
    @patch("graphrag_service.modules.health.services.get_neo4j_client")
    def test_check_neo4j_healthy(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.verify_connection.return_value = True
        mock_get_client.return_value = mock_client

        svc = HealthService()
        result = svc.check_neo4j()
        assert result.status == "healthy"
        assert result.name == "neo4j"
        assert result.response_time_ms is not None

    @patch("graphrag_service.modules.health.services.get_neo4j_client")
    def test_check_neo4j_unhealthy(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.verify_connection.return_value = False
        mock_get_client.return_value = mock_client

        svc = HealthService()
        result = svc.check_neo4j()
        assert result.status == "unhealthy"

    @patch("graphrag_service.modules.health.services.get_neo4j_client")
    def test_check_neo4j_exception(self, mock_get_client):
        mock_get_client.side_effect = Exception("connection refused")
        svc = HealthService()
        result = svc.check_neo4j()
        assert result.status == "unhealthy"
        assert "connection refused" in result.message

    @patch("graphrag_service.modules.health.services.get_neo4j_client")
    def test_get_basic_health_all_healthy(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.verify_connection.return_value = True
        mock_get_client.return_value = mock_client

        svc = HealthService()
        status, components, uptime = svc.get_basic_health()
        assert status == "healthy"
        assert len(components) == 1
        assert uptime > 0

    @patch("graphrag_service.modules.health.services.get_neo4j_client")
    def test_get_basic_health_unhealthy(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.verify_connection.return_value = False
        mock_get_client.return_value = mock_client

        svc = HealthService()
        status, _, _ = svc.get_basic_health()
        assert status == "unhealthy"
