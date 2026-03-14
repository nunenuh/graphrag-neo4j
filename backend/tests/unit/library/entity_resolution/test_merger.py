"""Tests for the merger module — canonical name selection + alias collection."""

import pytest

from graphrag_service.library.entity_resolution.merger import (
    MergedAuthor,
    merge_clusters,
)


class TestMergeClusters:
    """Tests for merge_clusters function."""

    def test_merge_single_cluster_picks_most_frequent_name(self) -> None:
        cluster = [
            {"uid": "author:g_hinton", "name": "G. Hinton"},
            {"uid": "author:g_hinton_2", "name": "Geoffrey Hinton"},
            {"uid": "author:g_hinton_3", "name": "Geoffrey Hinton"},
        ]
        results = merge_clusters([cluster])
        assert len(results) == 1
        assert results[0].name == "Geoffrey Hinton"
        assert "G. Hinton" in results[0].aliases

    def test_merge_preserves_all_original_uids(self) -> None:
        cluster = [
            {"uid": "author:j_smith", "name": "J. Smith"},
            {"uid": "author:john_smith", "name": "John Smith"},
        ]
        results = merge_clusters([cluster])
        assert set(results[0].original_uids) == {
            "author:j_smith",
            "author:john_smith",
        }

    def test_merge_generates_deterministic_uid(self) -> None:
        cluster = [
            {"uid": "a1", "name": "John Smith"},
            {"uid": "a2", "name": "J. Smith"},
        ]
        r1 = merge_clusters([cluster])
        r2 = merge_clusters([cluster])
        assert r1[0].uid == r2[0].uid

    def test_merge_multiple_clusters(self) -> None:
        clusters = [
            [{"uid": "a1", "name": "Alice"}, {"uid": "a2", "name": "A. Lee"}],
            [{"uid": "b1", "name": "Bob"}, {"uid": "b2", "name": "Robert"}],
        ]
        results = merge_clusters(clusters)
        assert len(results) == 2

    def test_merge_empty_clusters(self) -> None:
        assert merge_clusters([]) == []

    def test_merged_author_is_frozen(self) -> None:
        cluster = [
            {"uid": "a1", "name": "John Smith"},
            {"uid": "a2", "name": "J. Smith"},
        ]
        results = merge_clusters([cluster])
        with pytest.raises(AttributeError):
            results[0].name = "Modified"  # type: ignore[misc]

    def test_canonical_name_breaks_tie_by_longest(self) -> None:
        """When frequency is tied, pick the longest name."""
        cluster = [
            {"uid": "a1", "name": "J. Doe"},
            {"uid": "a2", "name": "Jane Doe"},
        ]
        results = merge_clusters([cluster])
        assert results[0].name == "Jane Doe"

    def test_aliases_exclude_canonical_name(self) -> None:
        cluster = [
            {"uid": "a1", "name": "Alice"},
            {"uid": "a2", "name": "Alice"},
            {"uid": "a3", "name": "A. Smith"},
        ]
        results = merge_clusters([cluster])
        assert results[0].name == "Alice"
        assert "Alice" not in results[0].aliases
        assert "A. Smith" in results[0].aliases

    def test_skip_empty_inner_cluster(self) -> None:
        results = merge_clusters([[]])
        assert results == []
