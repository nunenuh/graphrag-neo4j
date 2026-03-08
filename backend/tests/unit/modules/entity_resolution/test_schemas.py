"""Unit tests for modules/entity_resolution/schemas.py."""

from graphrag_service.modules.entity_resolution.schemas import (
    ERResolveResponse,
    ERStatsResponse,
)


class TestERStatsResponse:
    def test_create(self):
        stats = ERStatsResponse(
            total_authors=100,
            merged_authors=10,
            canonical_authors=90,
            total_authored_rels=500,
            clusters_found=5,
        )
        assert stats.total_authors == 100
        assert stats.canonical_authors == 90


class TestERResolveResponse:
    def test_create(self):
        resp = ERResolveResponse(
            blocks_processed=50,
            clusters_found=10,
            authors_merged=20,
            message="Done",
        )
        assert resp.authors_merged == 20
        assert resp.message == "Done"
