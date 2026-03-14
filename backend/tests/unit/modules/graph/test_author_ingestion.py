"""Tests for author ingestion orchestrator."""

from graphrag_service.library.entity_resolution.merger import MergedAuthor
from graphrag_service.modules.graph.author_ingestion import (
    prepare_author_nodes,
    prepare_coauthor_edges,
    run_entity_resolution,
)


def test_run_entity_resolution_merges_similar_names():
    raw_authors = [
        {"uid": "author:j_doe", "name": "J. Doe"},
        {"uid": "author:john_doe", "name": "John Doe"},
        {"uid": "author:jane_smith", "name": "Jane Smith"},
    ]
    merged, uid_mapping = run_entity_resolution(raw_authors)
    smith_authors = [
        a for a in merged if "Smith" in a.name or "smith" in a.name_normalized
    ]
    assert len(smith_authors) == 1


def test_prepare_author_nodes_returns_dicts():
    authors = [
        MergedAuthor(
            uid="author:abc123",
            name="John Doe",
            name_normalized="john doe",
            blocking_key="doe_j",
            aliases=("J. Doe",),
            original_uids=("author:j_doe", "author:john_doe"),
        )
    ]
    nodes = prepare_author_nodes(authors)
    assert len(nodes) == 1
    assert nodes[0]["uid"] == "author:abc123"
    assert nodes[0]["aliases"] == '["J. Doe"]'


def test_prepare_coauthor_edges_counts_shared_papers():
    author_paper_edges = [
        {"author_uid": "a", "paper_uid": "p1", "order": 0},
        {"author_uid": "b", "paper_uid": "p1", "order": 1},
        {"author_uid": "c", "paper_uid": "p1", "order": 2},
        {"author_uid": "a", "paper_uid": "p2", "order": 0},
        {"author_uid": "b", "paper_uid": "p2", "order": 1},
    ]
    edges = prepare_coauthor_edges(author_paper_edges)
    ab_edge = next(
        e for e in edges if set([e["from_uid"], e["to_uid"]]) == {"a", "b"}
    )
    assert ab_edge["paper_count"] == 2
    assert len(edges) == 3
