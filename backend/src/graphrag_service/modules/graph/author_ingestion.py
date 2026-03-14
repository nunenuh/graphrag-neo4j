"""Orchestrate author extraction, entity resolution, and edge preparation."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from itertools import combinations

from graphrag_service.library.entity_resolution import (
    build_blocks,
    compute_blocking_key,
    find_clusters,
    merge_clusters,
    normalize_name,
)
from graphrag_service.library.entity_resolution.merger import (
    MergedAuthor,
    deterministic_uid,
)

logger = logging.getLogger(__name__)


def run_entity_resolution(
    raw_authors: list[dict],
    threshold: float = 0.85,
) -> tuple[list[MergedAuthor], dict[str, str]]:
    """Run the full ER pipeline on raw author dicts.

    Steps: normalize -> block -> cluster -> merge -> handle standalone.

    Args:
        raw_authors: List of dicts with 'uid' and 'name' keys.
        threshold: Minimum similarity score for merging (0.0-1.0).

    Returns:
        Tuple of (canonical_authors, uid_mapping) where uid_mapping
        maps each original UID to its canonical UID.
    """
    for author in raw_authors:
        author["name_normalized"] = normalize_name(author["name"])
        author["blocking_key"] = compute_blocking_key(author["name"])

    blocks = build_blocks(raw_authors)
    logger.info("Built %d blocks from %d raw authors", len(blocks), len(raw_authors))

    all_clusters: list[list[dict]] = []
    clustered_uids: set[str] = set()
    for _key, block in blocks.items():
        clusters = find_clusters(block, threshold=threshold)
        for cluster in clusters:
            all_clusters.append(cluster)
            for a in cluster:
                clustered_uids.add(a["uid"])

    merged = merge_clusters(all_clusters)

    uid_mapping: dict[str, str] = {}
    for ma in merged:
        for orig_uid in ma.original_uids:
            uid_mapping[orig_uid] = ma.uid

    # Standalone authors (not in any cluster)
    standalone: list[MergedAuthor] = []
    for author in raw_authors:
        if author["uid"] not in clustered_uids:
            normalized = normalize_name(author["name"])
            uid = deterministic_uid(normalized)
            standalone.append(
                MergedAuthor(
                    uid=uid,
                    name=author["name"],
                    name_normalized=normalized,
                    blocking_key=compute_blocking_key(author["name"]),
                    aliases=(),
                    original_uids=(author["uid"],),
                )
            )
            uid_mapping[author["uid"]] = uid

    all_authors = merged + standalone
    logger.info(
        "Total: %d canonical (%d merged + %d standalone)",
        len(all_authors),
        len(merged),
        len(standalone),
    )
    return all_authors, uid_mapping


def prepare_author_nodes(authors: list[MergedAuthor]) -> list[dict]:
    """Convert MergedAuthor records into flat dicts for batch DB insertion.

    Args:
        authors: List of canonical MergedAuthor records.

    Returns:
        List of dicts ready for the repository layer.
    """
    return [
        {
            "uid": a.uid,
            "name": a.name,
            "name_normalized": a.name_normalized,
            "blocking_key": a.blocking_key,
            "aliases": json.dumps(list(a.aliases)),
        }
        for a in authors
    ]


def prepare_coauthor_edges(author_paper_edges: list[dict]) -> list[dict]:
    """Build co-author edges with paper counts from author-paper relationships.

    For every pair of authors who share at least one paper, produces an
    edge with the count of shared papers.

    Args:
        author_paper_edges: List of dicts with 'author_uid' and 'paper_uid' keys.

    Returns:
        List of dicts with 'from_uid', 'to_uid', and 'paper_count' keys.
        Pairs are sorted (from_uid < to_uid) for deterministic output.
    """
    papers: dict[str, list[str]] = defaultdict(list)
    for edge in author_paper_edges:
        papers[edge["paper_uid"]].append(edge["author_uid"])

    pair_counts: Counter[tuple[str, str]] = Counter()
    for _paper_uid, author_uids in papers.items():
        unique_authors = sorted(set(author_uids))
        for a, b in combinations(unique_authors, 2):
            pair_counts[(a, b)] += 1

    return [
        {"from_uid": a, "to_uid": b, "paper_count": count}
        for (a, b), count in pair_counts.items()
    ]
