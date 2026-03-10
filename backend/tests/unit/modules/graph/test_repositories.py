"""Unit tests for graph module repositories."""

import pytest
from unittest.mock import MagicMock

from tests.conftest import FakeNode
from graphrag_service.modules.graph.repositories import (
    GraphExploreRepository,
    NodeRepository,
    SchemaRepository,
    VALID_LABELS,
    _validate_label,
    _validate_rel_type,
)
from graphrag_service.shared.exceptions import RepositoryException


class TestValidateLabel:
    def test_valid_labels(self):
        for label in VALID_LABELS:
            assert _validate_label(label) == label

    def test_invalid_label_raises(self):
        with pytest.raises(ValueError, match="Invalid label"):
            _validate_label("Hacker")

    def test_case_sensitive(self):
        with pytest.raises(ValueError):
            _validate_label("paper")


class TestValidateRelType:
    def test_valid_rel_types(self):
        assert _validate_rel_type("USED_FOR") == "USED_FOR"
        assert _validate_rel_type("EVALUATED_ON") == "EVALUATED_ON"
        assert _validate_rel_type("A") == "A"

    def test_invalid_rel_types(self):
        with pytest.raises(ValueError, match="Invalid relationship type"):
            _validate_rel_type("used_for")

        with pytest.raises(ValueError):
            _validate_rel_type("DROP DATABASE")

        with pytest.raises(ValueError):
            _validate_rel_type("")

        with pytest.raises(ValueError):
            _validate_rel_type("123ABC")


class TestSchemaRepository:
    def test_get_labels(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = [{"l": ["Paper", "Method"]}]
        repo = SchemaRepository(mock_neo4j_client)
        labels = repo.get_labels()
        assert labels == ["Paper", "Method"]

    def test_get_labels_empty(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        repo = SchemaRepository(mock_neo4j_client)
        assert repo.get_labels() == []

    def test_get_labels_raises_repository_exception(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = Exception("conn failed")
        repo = SchemaRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Failed to get labels"):
            repo.get_labels()

    def test_get_relationship_types(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = [{"r": ["USED_FOR"]}]
        repo = SchemaRepository(mock_neo4j_client)
        rels = repo.get_relationship_types()
        assert rels == ["USED_FOR"]

    def test_get_schema(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"l": ["Paper"]}],
            [{"r": ["USED_FOR"]}],
        ]
        repo = SchemaRepository(mock_neo4j_client)
        labels, rels = repo.get_schema()
        assert labels == ["Paper"]
        assert rels == ["USED_FOR"]


class TestNodeRepository:
    def test_upsert_batch(self, mock_neo4j_client):
        from graphrag_service.dbase.neo4j.models import Paper
        repo = NodeRepository(mock_neo4j_client)
        nodes = [{"uid": "p1", "title": "T", "abstract": "A", "year": "2024", "url": ""}]
        embeddings = [[0.1, 0.2]]
        repo.upsert_batch(Paper, nodes, embeddings)
        mock_neo4j_client.run_query.assert_called_once()

    def test_upsert_batch_raises_on_db_error(self, mock_neo4j_client):
        from graphrag_service.dbase.neo4j.models import Paper
        mock_neo4j_client.run_query.side_effect = Exception("db error")
        repo = NodeRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Failed to upsert Paper"):
            repo.upsert_batch(Paper, [{"uid": "p1"}], [[0.1]])

    def test_merge_used_for(self, mock_neo4j_client):
        repo = NodeRepository(mock_neo4j_client)
        repo.merge_used_for("CIFAR-10", "Image Classification")
        call_args = mock_neo4j_client.run_query.call_args
        assert "MERGE" in call_args[0][0]
        assert call_args[0][1]["dname"] == "CIFAR-10"

    def test_merge_evaluated_on(self, mock_neo4j_client):
        repo = NodeRepository(mock_neo4j_client)
        repo.merge_evaluated_on("ResNet", "CIFAR-10", "accuracy", "95.5")
        call_args = mock_neo4j_client.run_query.call_args
        assert call_args[0][1]["mname"] == "ResNet"
        assert call_args[0][1]["metric"] == "accuracy"


class TestGraphExploreRepository:
    def test_explore_returns_nodes_and_edges(self, mock_neo4j_client):
        node_a = FakeNode({"uid": "a1", "name": "A"}, labels={"Paper"})
        node_b = FakeNode({"uid": "b1", "name": "B"}, labels={"Task"})

        mock_neo4j_client.run_query.return_value = [
            {"a": node_a, "b": node_b, "rel": "USED_FOR"}
        ]
        repo = GraphExploreRepository(mock_neo4j_client)
        nodes, edges = repo.explore(limit=10)
        assert len(nodes) == 2
        assert len(edges) == 1
        assert edges[0]["type"] == "USED_FOR"

    def test_explore_raises_repository_exception(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = Exception("fail")
        repo = GraphExploreRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Failed to explore"):
            repo.explore()

    def test_get_stats(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"c": 5}],   # Author
            [{"c": 10}],  # Paper
            [{"c": 20}],  # Method
            [{"c": 30}],  # Task
            [{"c": 40}],  # Dataset
            [{"t": "USED_FOR"}, {"t": "EVALUATED_ON"}],
            [{"c": 5}],
            [{"c": 3}],
        ]
        repo = GraphExploreRepository(mock_neo4j_client)
        stats = repo.get_stats()
        assert stats["total_nodes"] == 105
        assert stats["total_edges"] == 8
        assert stats["node_counts"]["Paper"] == 10
        assert stats["edge_counts"]["USED_FOR"] == 5

    def test_get_node_by_uid_found(self, mock_neo4j_client):
        node = FakeNode({"uid": "p1", "name": "Paper1"}, labels={"Paper"})
        mock_neo4j_client.run_query.return_value = [
            {
                "n": node,
                "label": "Paper",
                "outgoing": [{"to": "t1", "type": "USED_FOR"}],
                "incoming": [],
            }
        ]
        repo = GraphExploreRepository(mock_neo4j_client)
        result = repo.get_node_by_uid("p1")
        assert result["uid"] == "p1"
        assert result["label"] == "Paper"
        assert len(result["outgoing"]) == 1

    def test_get_node_by_uid_not_found(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        repo = GraphExploreRepository(mock_neo4j_client)
        assert repo.get_node_by_uid("nonexistent") is None

    def test_search_nodes_no_label(self, mock_neo4j_client):
        node = FakeNode({"uid": "m1", "name": "ResNet"}, labels={"Method"})
        mock_neo4j_client.run_query.return_value = [
            {"n": node, "label": "Method"}
        ]
        repo = GraphExploreRepository(mock_neo4j_client)
        results = repo.search_nodes("res")
        assert len(results) == 1
        assert results[0]["name"] == "ResNet"

    def test_search_nodes_with_label(self, mock_neo4j_client):
        node = FakeNode({"uid": "m1", "name": "ResNet"}, labels={"Method"})
        mock_neo4j_client.run_query.return_value = [
            {"n": node, "label": "Method"}
        ]
        repo = GraphExploreRepository(mock_neo4j_client)
        results = repo.search_nodes("res", label="Method")
        assert len(results) == 1
        cypher = mock_neo4j_client.run_query.call_args[0][0]
        assert "Method" in cypher

    def test_search_nodes_invalid_label(self, mock_neo4j_client):
        repo = GraphExploreRepository(mock_neo4j_client)
        with pytest.raises(ValueError, match="Invalid label"):
            repo.search_nodes("test", label="InvalidLabel")

    def test_search_nodes_db_error(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = Exception("db error")
        repo = GraphExploreRepository(mock_neo4j_client)
        with pytest.raises(RepositoryException, match="Node search failed"):
            repo.search_nodes("test")
