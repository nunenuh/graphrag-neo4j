"""Unit tests for RAG module repositories."""

import pytest
from unittest.mock import MagicMock

from tests.conftest import FakeNode
from graphrag_service.modules.rag.repositories import (
    TraversalRepository,
    VectorSearchRepository,
    VectorSearchResult,
)
from graphrag_service.shared.exceptions import RepositoryException


class TestVectorSearchResult:
    def test_immutable(self):
        r = VectorSearchResult(id="1", label="Paper", name="P1", score=0.9)
        with pytest.raises(AttributeError):
            r.id = "2"

    def test_default_properties(self):
        r = VectorSearchResult(id="1", label="Paper", name="P1", score=0.9)
        assert r.properties == {}


class TestVectorSearchRepository:
    def test_search_single_label(self, mock_neo4j_client):
        node = FakeNode({"uid": "p1", "name": "Paper1"}, labels={"Paper"})
        mock_neo4j_client.run_query.return_value = [
            {"node": node, "score": 0.95, "label": "Paper"}
        ]
        repo = VectorSearchRepository(mock_neo4j_client)
        results = repo.search([0.1] * 3, "Paper", 5)
        assert len(results) == 1
        assert results[0].id == "p1"
        assert results[0].score == 0.95

    def test_search_raises_repository_exception(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = Exception("vector fail")
        repo = VectorSearchRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Vector search failed"):
            repo.search([0.1], "Paper", 5)

    def test_search_all_aggregates_and_sorts(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"node": FakeNode({"uid": "p1", "name": "P1"}), "score": 0.8, "label": "Paper"}],
            [{"node": FakeNode({"uid": "m1", "name": "M1"}), "score": 0.95, "label": "Method"}],
            [{"node": FakeNode({"uid": "t1", "name": "T1"}), "score": 0.7, "label": "Task"}],
            [{"node": FakeNode({"uid": "d1", "name": "D1"}), "score": 0.6, "label": "Dataset"}],
        ]
        repo = VectorSearchRepository(mock_neo4j_client)
        results = repo.search_all([0.1], k=2)
        assert len(results) == 2
        assert results[0].score == 0.95
        assert results[1].score == 0.8

    def test_search_all_empty(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        repo = VectorSearchRepository(mock_neo4j_client)
        results = repo.search_all([0.1], k=5)
        assert results == []


class TestTraversalRepository:
    def test_traverse_empty(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        repo = TraversalRepository(mock_neo4j_client)
        nodes, edges, path = repo.traverse(["p1"])
        assert nodes == {}
        assert edges == []
        assert path == [{"hop": 0, "node_count": 0, "node_labels": [], "edge_types": [], "description": "Vector search found 0 seed nodes"}]

    def test_traverse_raises_repository_exception(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = Exception("traverse fail")
        repo = TraversalRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Graph traversal failed"):
            repo.traverse(["p1"])

    def test_traverse_with_data(self, mock_neo4j_client):
        seed = FakeNode({"uid": "p1", "name": "Paper1"})
        n1 = FakeNode({"uid": "t1", "name": "Task1"})

        mock_neo4j_client.run_query.return_value = [
            {
                "seed": seed,
                "seed_label": "Paper",
                "nodes1": [{"node": n1, "label": "Task"}],
                "nodes2": [],
                "e1": [{"from": "p1", "to": "t1", "type": "USED_FOR", "props": {}}],
                "e2": [],
            }
        ]
        repo = TraversalRepository(mock_neo4j_client)
        nodes, edges, path = repo.traverse(["p1"])
        assert "p1" in nodes
        assert "t1" in nodes
        assert len(edges) == 1
        assert edges[0]["type"] == "USED_FOR"
        assert path[0]["hop"] == 0
        assert path[1]["hop"] == 1
        assert "USED_FOR" in path[1]["edge_types"]

    def test_traverse_filters_none_nodes(self, mock_neo4j_client):
        seed = FakeNode({"uid": "p1"})
        mock_neo4j_client.run_query.return_value = [
            {
                "seed": seed,
                "nodes1": [None],
                "nodes2": None,
                "e1": [{"from": "p1", "to": None, "type": "REL", "props": {}}],
                "e2": None,
            }
        ]
        repo = TraversalRepository(mock_neo4j_client)
        nodes, edges, path = repo.traverse(["p1"])
        assert len(nodes) == 1
        assert edges == []
