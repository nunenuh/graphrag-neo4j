"""Unit tests for modules/entity_resolution/services.py."""

import pytest

from graphrag_service.modules.entity_resolution.services import ERService


class TestPrepareAuthorForUpsert:
    def test_basic(self):
        author = {"uid": "author:geoffrey_hinton", "name": "Geoffrey Hinton"}
        result = ERService.prepare_author_for_upsert(author)
        assert result["name_normalized"] == "geoffrey hinton"
        assert result["blocking_key"] == "hinton_g"
        assert result["aliases"] == "[]"
        assert result["uid"] == "author:geoffrey_hinton"

    def test_diacritics(self):
        author = {"uid": "author:soren_muller", "name": "Sören Müller"}
        result = ERService.prepare_author_for_upsert(author)
        assert result["name_normalized"] == "soren muller"
        assert result["blocking_key"] == "muller_s"


class TestPrepareEdgeForMerge:
    def test_basic(self):
        edge = {"author_name": "Geoffrey Hinton", "paper_uid": "http://paper1", "order": 0}
        result = ERService.prepare_edge_for_merge(edge)
        assert result["author_uid"] == "author:geoffrey_hinton"
        assert result["paper_uid"] == "http://paper1"
        assert result["order"] == 0


class TestPickCanonical:
    def test_picks_longest_name(self):
        cluster = [
            {"uid": "1", "name": "G. Hinton"},
            {"uid": "2", "name": "Geoffrey Hinton"},
            {"uid": "3", "name": "Geoffrey E. Hinton"},
        ]
        canonical, duplicates = ERService.pick_canonical(cluster)
        assert canonical["uid"] == "3"  # "Geoffrey E. Hinton" is longest
        assert len(duplicates) == 2

    def test_single_item(self):
        cluster = [{"uid": "1", "name": "Alice"}]
        canonical, duplicates = ERService.pick_canonical(cluster)
        assert canonical["uid"] == "1"
        assert duplicates == []


class TestResolveBlocks:
    def test_finds_clusters(self):
        authors = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "Geoffrey E. Hinton"},
            {"uid": "3", "name": "Yann LeCun"},
        ]
        clusters = ERService.resolve_blocks(authors, threshold=0.7, max_block_size=500)
        # Hinton variants should cluster, LeCun should not
        assert len(clusters) >= 1

    def test_no_clusters_high_threshold(self):
        authors = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "George Humphrey"},
        ]
        clusters = ERService.resolve_blocks(authors, threshold=0.99, max_block_size=500)
        assert len(clusters) == 0

    def test_empty_input(self):
        clusters = ERService.resolve_blocks([], threshold=0.85, max_block_size=500)
        assert clusters == []
