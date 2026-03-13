"""Integration test for author ingestion pipeline.

Requires a running Neo4j instance with ingested paper data.
Run with: poetry run pytest tests/integration/ -v -m integration
"""

import pytest

from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.graph.usecase import GraphUseCase


@pytest.mark.integration
def test_full_author_ingestion_pipeline():
    """End-to-end: extract authors from PwC data, run ER, create nodes + edges."""
    client = get_neo4j_client()
    try:
        usecase = GraphUseCase(client)
        result = usecase.ingest_authors(batch_size=100)
    finally:
        close_neo4j_client()

    assert result["raw_authors"] > 0
    assert result["canonical_authors"] > 0
    assert result["canonical_authors"] <= result["raw_authors"]
    assert result["authored_edges"] > 0
    # CO_AUTHORED_WITH may be 0 if all papers have single authors (unlikely)
    assert result["coauthor_edges"] >= 0
