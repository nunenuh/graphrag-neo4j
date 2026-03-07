"""
Shared test fixtures for the GraphRAG service test suite.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class FakeNode(dict):
    """A dict subclass that also has a .labels attribute, mimicking neo4j nodes."""

    def __init__(self, data: dict, labels: set[str] | None = None):
        super().__init__(data)
        self.labels = labels or set()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Set minimal env vars so Settings can instantiate without .env file."""
    monkeypatch.setenv("APP_X_API_KEY", "test-api-key")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "testpass")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_ENVIRONMENT", "development")


@pytest.fixture()
def settings(_env_defaults):
    """Fresh Settings instance (cache cleared)."""
    from graphrag_service.core.config import Settings, get_settings

    get_settings.cache_clear()
    s = get_settings()
    yield s
    get_settings.cache_clear()


@pytest.fixture()
def mock_neo4j_client():
    """A MagicMock standing in for Neo4jClient."""
    client = MagicMock()
    client.run_query = MagicMock(return_value=[])
    client.verify_connection = MagicMock(return_value=True)
    client.install_labels = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture()
def api_key():
    return "test-api-key"


@pytest.fixture()
def auth_headers(api_key):
    return {"X-API-Key": api_key}


@pytest.fixture()
def app(mock_neo4j_client, settings):
    """FastAPI TestClient with mocked Neo4j dependency."""
    from graphrag_service.core.config import get_settings
    from graphrag_service.core.dependencies import get_neo4j_client
    from graphrag_service.main import create_app

    application = create_app()
    application.dependency_overrides[get_neo4j_client] = lambda: mock_neo4j_client
    yield application
    application.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    """TestClient for the FastAPI app."""
    return TestClient(app)
