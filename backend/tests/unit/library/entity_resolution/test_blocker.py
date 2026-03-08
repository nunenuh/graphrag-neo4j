"""Unit tests for library/entity_resolution/blocker.py."""

import pytest

from graphrag_service.library.entity_resolution.blocker import (
    _UnionFind,
    build_blocks,
    find_clusters,
)


class TestUnionFind:
    def test_find_creates_set(self):
        uf = _UnionFind()
        assert uf.find("a") == "a"

    def test_union_and_find(self):
        uf = _UnionFind()
        uf.union("a", "b")
        assert uf.find("a") == uf.find("b")

    def test_three_way_union(self):
        uf = _UnionFind()
        uf.union("a", "b")
        uf.union("b", "c")
        assert uf.find("a") == uf.find("c")

    def test_clusters(self):
        uf = _UnionFind()
        uf.union("a", "b")
        uf.find("c")  # singleton
        clusters = uf.clusters()
        # Should have 2 groups: {a, b} and {c}
        assert len(clusters) == 2
        for members in clusters.values():
            assert len(members) in [1, 2]


class TestBuildBlocks:
    def test_groups_by_blocking_key(self):
        authors = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "G. Hinton"},
            {"uid": "3", "name": "Yann LeCun"},
        ]
        blocks = build_blocks(authors)
        # Hinton_g should have 2 authors
        assert "hinton_g" in blocks
        assert len(blocks["hinton_g"]) == 2

    def test_singletons_excluded(self):
        authors = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "Yann LeCun"},
        ]
        blocks = build_blocks(authors)
        # Each blocking key has only 1 author → all excluded
        assert len(blocks) == 0

    def test_max_block_size(self):
        # Create a block with 3 authors
        authors = [
            {"uid": f"{i}", "name": f"Person{i} Smith"}
            for i in range(3)
        ]
        # max_block_size=2 should exclude the block of 3
        blocks = build_blocks(authors, max_block_size=2)
        assert len(blocks) == 0

    def test_empty_input(self):
        assert build_blocks([]) == {}


class TestFindClusters:
    def test_merges_similar_names(self):
        block = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "Geoffrey E. Hinton"},
        ]
        clusters = find_clusters(block, threshold=0.7)
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_no_merge_below_threshold(self):
        block = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "George Humphrey"},
        ]
        clusters = find_clusters(block, threshold=0.95)
        assert len(clusters) == 0

    def test_single_author(self):
        block = [{"uid": "1", "name": "Geoffrey Hinton"}]
        assert find_clusters(block) == []

    def test_empty_block(self):
        assert find_clusters([]) == []

    def test_three_way_cluster(self):
        block = [
            {"uid": "1", "name": "Geoffrey Hinton"},
            {"uid": "2", "name": "Geoffrey E. Hinton"},
            {"uid": "3", "name": "Geoffrey E Hinton"},
        ]
        clusters = find_clusters(block, threshold=0.7)
        # All three should end up in one cluster
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
