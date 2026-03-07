"""Unit tests for graph module usecase."""

from unittest.mock import MagicMock, patch

from graphrag_service.modules.graph.usecase import GraphUseCase


class TestGraphUseCase:
    def test_get_schema_delegates(self, mock_neo4j_client):
        mock_neo4j_client.run_query.side_effect = [
            [{"l": ["Paper"]}],
            [{"r": ["USED_FOR"]}],
        ]
        uc = GraphUseCase(mock_neo4j_client)
        labels, rels = uc.get_schema()
        assert labels == ["Paper"]
        assert rels == ["USED_FOR"]

    def test_explore_delegates(self, mock_neo4j_client):
        mock_neo4j_client.run_query.return_value = []
        uc = GraphUseCase(mock_neo4j_client)
        nodes, edges = uc.explore(limit=10)
        assert nodes == []
        assert edges == []

    def test_get_stats_delegates(self, mock_neo4j_client):
        uc = GraphUseCase(mock_neo4j_client)
        uc.explore_repo = MagicMock()
        uc.explore_repo.get_stats.return_value = {"total_nodes": 5}
        assert uc.get_stats() == {"total_nodes": 5}

    def test_get_node_delegates(self, mock_neo4j_client):
        uc = GraphUseCase(mock_neo4j_client)
        uc.explore_repo = MagicMock()
        uc.explore_repo.get_node_by_uid.return_value = {"uid": "p1"}
        assert uc.get_node("p1") == {"uid": "p1"}

    def test_search_nodes_delegates(self, mock_neo4j_client):
        uc = GraphUseCase(mock_neo4j_client)
        uc.explore_repo = MagicMock()
        uc.explore_repo.search_nodes.return_value = [{"uid": "m1"}]
        result = uc.search_nodes("res", label="Method", limit=5)
        assert result == [{"uid": "m1"}]
        uc.explore_repo.search_nodes.assert_called_once_with("res", label="Method", limit=5)
