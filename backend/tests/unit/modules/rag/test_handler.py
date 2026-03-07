"""Unit tests for RAG API handler endpoint."""

from unittest.mock import patch

import pytest


class TestRAGQueryEndpoint:
    @patch("graphrag_service.modules.rag.apiv1.handler.RAGUseCase")
    def test_success(self, MockUseCase, client, auth_headers):
        mock_uc = MockUseCase.return_value
        mock_uc.query.return_value = {
            "answer": "ResNet is a deep learning model.",
            "subgraph": {
                "seed_nodes": [
                    {"id": "m1", "label": "Method", "name": "ResNet", "score": 0.95}
                ],
                "nodes": [{"uid": "m1", "name": "ResNet"}],
                "edges": [
                    {"from_id": "m1", "to_id": "d1", "type": "EVALUATED_ON", "properties": {}}
                ],
                "cypher_used": "test query",
            },
        }
        resp = client.post(
            "/api/v1/rag/query",
            json={"question": "What is ResNet?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ResNet" in data["answer"]
        assert data["seed_nodes"][0]["name"] == "ResNet"
        assert len(data["edges"]) == 1
        assert data["latency_ms"] >= 0

    def test_no_auth_returns_403(self, client):
        resp = client.post("/api/v1/rag/query", json={"question": "test"})
        assert resp.status_code == 403

    def test_empty_question_returns_422(self, client, auth_headers):
        resp = client.post(
            "/api/v1/rag/query",
            json={"question": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_question_returns_422(self, client, auth_headers):
        resp = client.post("/api/v1/rag/query", json={}, headers=auth_headers)
        assert resp.status_code == 422

    @patch("graphrag_service.modules.rag.apiv1.handler.RAGUseCase")
    def test_service_exception_returns_503(self, MockUseCase, client, auth_headers):
        from graphrag_service.shared.exceptions import ServiceException
        mock_uc = MockUseCase.return_value
        mock_uc.query.side_effect = ServiceException("LLM down")
        resp = client.post(
            "/api/v1/rag/query",
            json={"question": "test question"},
            headers=auth_headers,
        )
        assert resp.status_code == 503

    @patch("graphrag_service.modules.rag.apiv1.handler.RAGUseCase")
    def test_unexpected_error_returns_500(self, MockUseCase, client, auth_headers):
        mock_uc = MockUseCase.return_value
        mock_uc.query.side_effect = RuntimeError("unexpected")
        resp = client.post(
            "/api/v1/rag/query",
            json={"question": "test question"},
            headers=auth_headers,
        )
        assert resp.status_code == 500

    def test_question_max_length(self, client, auth_headers):
        long_q = "a" * 2001
        resp = client.post(
            "/api/v1/rag/query",
            json={"question": long_q},
            headers=auth_headers,
        )
        assert resp.status_code == 422
