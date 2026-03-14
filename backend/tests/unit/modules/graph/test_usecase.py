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


def test_ingest_authors_calls_er_pipeline():
    mock_client = MagicMock()
    usecase = GraphUseCase(mock_client)
    mock_authors = [{"uid": "author:john_doe", "name": "John Doe"}]
    mock_edges = [{"author_name": "John Doe", "paper_uid": "paper:123", "order": 0}]

    with patch("graphrag_service.modules.graph.usecase.iter_authors", return_value=iter(mock_authors)), \
         patch("graphrag_service.modules.graph.usecase.iter_author_paper_edges", return_value=iter(mock_edges)), \
         patch("graphrag_service.modules.graph.usecase.load_json", return_value=[]), \
         patch("graphrag_service.modules.graph.usecase.run_entity_resolution") as mock_er, \
         patch("graphrag_service.modules.graph.usecase.prepare_author_nodes") as mock_prep, \
         patch("graphrag_service.modules.graph.usecase.prepare_coauthor_edges") as mock_coauth, \
         patch.object(usecase, "_upsert_without_embedding"):

        from graphrag_service.library.entity_resolution.merger import MergedAuthor
        mock_er.return_value = (
            [MergedAuthor(uid="author:abc", name="John Doe", name_normalized="john doe",
                          blocking_key="doe_j", aliases=(), original_uids=("author:john_doe",))],
            {"author:john_doe": "author:abc"},
        )
        mock_prep.return_value = [{"uid": "author:abc", "name": "John Doe"}]
        mock_coauth.return_value = []

        usecase.ingest_authors()
        mock_er.assert_called_once()
        mock_prep.assert_called_once()
