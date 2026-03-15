"""Unit tests for graph API handler endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import FakeNode
from graphrag_service.shared.exceptions import RepositoryException


class TestGraphSchemaEndpoint:
    def test_success(self, client, auth_headers, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"l": ["Paper", "Method"]}],
            [{"r": ["USED_FOR"]}],
        ]
        resp = client.get("/api/v1/graph/schema", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_labels"] == ["Paper", "Method"]
        assert data["relationship_types"] == ["USED_FOR"]

    def test_no_auth_returns_403(self, client):
        resp = client.get("/api/v1/graph/schema")
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self, client):
        resp = client.get("/api/v1/graph/schema", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403

    def test_db_error_returns_503(self, client, auth_headers, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = RepositoryException("db down")
        resp = client.get("/api/v1/graph/schema", headers=auth_headers)
        assert resp.status_code == 503


class TestGraphExploreEndpoint:
    def test_success_empty(self, client, auth_headers, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        resp = client.get("/api/v1/graph/explore?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_limit_validation(self, client, auth_headers):
        resp = client.get("/api/v1/graph/explore?limit=0", headers=auth_headers)
        assert resp.status_code == 422

        resp = client.get("/api/v1/graph/explore?limit=201", headers=auth_headers)
        assert resp.status_code == 422


class TestGraphStatsEndpoint:
    def test_success(self, client, auth_headers, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"c": 5}],   # Author
            [{"c": 10}], [{"c": 20}], [{"c": 30}], [{"c": 40}],
            [{"c": 2}],   # Repository
            [{"t": "USED_FOR"}],
            [{"c": 5}],
        ]
        resp = client.get("/api/v1/graph/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 107
        assert "node_counts" in data


class TestNodeDetailEndpoint:
    def test_not_found(self, client, auth_headers, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        resp = client.get("/api/v1/graph/nodes/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    def test_found(self, client, auth_headers, mock_neo4j_client):
        node = FakeNode({"uid": "p1", "name": "Paper1"}, labels={"Paper"})
        mock_neo4j_client.run_query.return_value = [
            {
                "n": node,
                "label": "Paper",
                "outgoing": [{"to": "t1", "type": "USED_FOR"}],
                "incoming": [],
            }
        ]
        resp = client.get("/api/v1/graph/nodes/p1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["uid"] == "p1"


class TestNodeSearchEndpoint:
    def test_success(self, client, auth_headers, mock_neo4j_client):
        node = FakeNode({"uid": "m1", "name": "ResNet"}, labels={"Method"})
        mock_neo4j_client.run_query.return_value = [
            {"n": node, "label": "Method"}
        ]
        resp = client.get("/api/v1/graph/search?q=res", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "ResNet"

    def test_missing_query_returns_422(self, client, auth_headers):
        resp = client.get("/api/v1/graph/search", headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_label_returns_400(self, client, auth_headers, mock_neo4j_client):
        resp = client.get("/api/v1/graph/search?q=test&label=Invalid", headers=auth_headers)
        assert resp.status_code == 400
