"""Blocking and clustering for entity resolution.

Groups authors by blocking key (last_name + first_initial) and
runs pairwise scoring within each block to find clusters of
matching authors using Union-Find.
"""

from collections import defaultdict
from itertools import combinations

from .normalizer import compute_blocking_key
from .scorer import score_pair


class _UnionFind:
    """Disjoint-set data structure for clustering."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def clusters(self) -> dict[str, list[str]]:
        """Return a mapping of root → list of members."""
        groups: dict[str, list[str]] = defaultdict(list)
        for x in self._parent:
            groups[self.find(x)].append(x)
        return dict(groups)


def build_blocks(
    authors: list[dict],
    max_block_size: int = 500,
) -> dict[str, list[dict]]:
    """Group authors by blocking key.

    Args:
        authors: List of dicts with at least 'name' and 'uid' keys.
        max_block_size: Skip blocks larger than this (too ambiguous).

    Returns:
        Dict mapping blocking_key → list of author dicts.
    """
    blocks: dict[str, list[dict]] = defaultdict(list)
    for author in authors:
        key = compute_blocking_key(author["name"])
        if key:
            blocks[key].append(author)

    # Filter out oversized blocks
    return {k: v for k, v in blocks.items() if 1 < len(v) <= max_block_size}


def find_clusters(
    block: list[dict],
    threshold: float = 0.85,
) -> list[list[dict]]:
    """Find clusters of matching authors within a block.

    Runs pairwise scoring on all authors in the block and uses
    Union-Find to group those above the similarity threshold.

    Args:
        block: List of author dicts from a single blocking group.
        threshold: Minimum similarity score to merge.

    Returns:
        List of clusters, each a list of author dicts. Only clusters
        with 2+ members are returned (singletons are skipped).
    """
    if len(block) < 2:
        return []

    uf = _UnionFind()
    # Initialize all UIDs
    for author in block:
        uf.find(author["uid"])

    # Pairwise comparison
    for a, b in combinations(block, 2):
        sim = score_pair(a["name"], b["name"])
        if sim >= threshold:
            uf.union(a["uid"], b["uid"])

    # Build clusters
    uid_to_author = {a["uid"]: a for a in block}
    raw_clusters = uf.clusters()

    result = []
    for members in raw_clusters.values():
        if len(members) >= 2:
            result.append([uid_to_author[uid] for uid in members])

    return result
