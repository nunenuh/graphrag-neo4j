"""Merge entity resolution clusters into canonical author records."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from graphrag_service.library.entity_resolution.normalizer import (
    compute_blocking_key,
    normalize_name,
)


@dataclass(frozen=True)
class MergedAuthor:
    """Canonical author record produced by merging a cluster."""

    uid: str
    name: str
    name_normalized: str
    blocking_key: str
    aliases: tuple[str, ...]
    original_uids: tuple[str, ...]


def deterministic_uid(name_normalized: str) -> str:
    """Generate a deterministic UID from a normalized name.

    Uses SHA-256 hash truncated to 12 hex chars for a compact,
    collision-resistant identifier.
    """
    h = hashlib.sha256(name_normalized.encode()).hexdigest()[:12]
    return f"author:{h}"


def _pick_canonical_name(names: list[str]) -> str:
    """Pick the canonical name from a list of name variants.

    Strategy:
    1. Pick the most frequently occurring name.
    2. Break ties by choosing the longest name (more informative).
    """
    counts = Counter(names)
    max_count = max(counts.values())
    candidates = [n for n, c in counts.items() if c == max_count]
    return max(candidates, key=len)


def merge_clusters(clusters: list[list[dict]]) -> list[MergedAuthor]:
    """Merge clusters of similar authors into canonical records.

    Args:
        clusters: List of clusters, each a list of author dicts
            with 'uid' and 'name' keys (output of blocker.find_clusters).

    Returns:
        List of MergedAuthor records, one per non-empty cluster.
    """
    results: list[MergedAuthor] = []
    for cluster in clusters:
        if not cluster:
            continue
        names = [a["name"] for a in cluster]
        canonical = _pick_canonical_name(names)
        normalized = normalize_name(canonical)
        aliases = tuple(sorted(set(n for n in names if n != canonical)))
        results.append(
            MergedAuthor(
                uid=deterministic_uid(normalized),
                name=canonical,
                name_normalized=normalized,
                blocking_key=compute_blocking_key(canonical),
                aliases=aliases,
                original_uids=tuple(a["uid"] for a in cluster),
            )
        )
    return results
