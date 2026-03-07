"""Unit tests for health API handler endpoints."""

from unittest.mock import patch


class TestPingEndpoint:
    def test_ping(self, client):
        resp = client.get("/api/v1/health/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["message"] == "pong"
        assert "timestamp" in data

    def test_ping_no_auth_required(self, client):
        resp = client.get("/api/v1/health/ping")
        assert resp.status_code == 200


class TestHealthStatusEndpoint:
    @patch("graphrag_service.modules.health.apiv1.handler.HealthUseCase")
    def test_healthy(self, MockUseCase, client):
        from graphrag_service.modules.health.schemas import ComponentHealth
        mock_uc = MockUseCase.return_value
        mock_uc.get_basic_health.return_value = (
            "healthy",
            [ComponentHealth(name="neo4j", status="healthy", message="Connected", response_time_ms=5.0)],
            123.4,
        )
        resp = client.get("/api/v1/health/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["components"][0]["name"] == "neo4j"
        assert "version" in data
        assert data["uptime_seconds"] == 123.4

    @patch("graphrag_service.modules.health.apiv1.handler.HealthUseCase")
    def test_unhealthy(self, MockUseCase, client):
        mock_uc = MockUseCase.return_value
        mock_uc.get_basic_health.side_effect = Exception("check failed")
        resp = client.get("/api/v1/health/status")
        assert resp.status_code == 503
