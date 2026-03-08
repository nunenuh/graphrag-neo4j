"""Entity resolution service — orchestrates library calls for ER.

Does NOT access the database. Uses library/ for normalization, scoring, blocking.
"""

import json
from pathlib import Path
from typing import Iterator

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.library.entity_resolution import (
    build_blocks,
    compute_blocking_key,
    find_clusters,
    normalize_name,
)
from graphrag_service.library.parsers import (
    iter_author_paper_edges,
    iter_authors,
    load_json,
)


class ERService:
    """Service for entity resolution logic. Does NOT access the database."""

    @staticmethod
    def data_dir() -> Path:
        settings = get_settings()
        path = Path(settings.DATA_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).parent.parent.parent.parent.parent.parent / settings.DATA_DIR

    def load_authors(self) -> Iterator[dict]:
        """Load and parse unique authors from papers JSON."""
        settings = get_settings()
        data = load_json(self.data_dir() / "papers.json")
        return iter_authors(data, max_papers=settings.MAX_PAPERS)

    def load_author_paper_edges(self) -> Iterator[dict]:
        """Load author-paper edges from papers JSON."""
        settings = get_settings()
        data = load_json(self.data_dir() / "papers.json")
        return iter_author_paper_edges(data, max_papers=settings.MAX_PAPERS)

    @staticmethod
    def prepare_author_for_upsert(author: dict) -> dict:
        """Enrich an author dict with normalized name and blocking key."""
        name = author["name"]
        return {
            **author,
            "name_normalized": normalize_name(name),
            "blocking_key": compute_blocking_key(name),
            "aliases": "[]",
        }

    @staticmethod
    def prepare_edge_for_merge(edge: dict) -> dict:
        """Prepare an author-paper edge for MERGE."""
        author_uid = f"author:{edge['author_name'].lower().replace(' ', '_')}"
        return {
            "author_uid": author_uid,
            "paper_uid": edge["paper_uid"],
            "order": edge["order"],
        }

    @staticmethod
    def resolve_blocks(
        authors: list[dict],
        threshold: float,
        max_block_size: int,
    ) -> list[list[dict]]:
        """Run blocking + clustering on a list of author dicts.

        Returns a list of clusters (each cluster is a list of author dicts).
        """
        blocks = build_blocks(authors, max_block_size=max_block_size)
        logger.info(f"Built {len(blocks)} blocks from {len(authors)} authors")

        all_clusters: list[list[dict]] = []
        for block_key, block_authors in blocks.items():
            clusters = find_clusters(block_authors, threshold=threshold)
            all_clusters.extend(clusters)

        logger.info(f"Found {len(all_clusters)} clusters to merge")
        return all_clusters

    @staticmethod
    def pick_canonical(cluster: list[dict]) -> tuple[dict, list[dict]]:
        """Pick the canonical author from a cluster.

        Heuristic: the longest name is most likely the full name.
        Returns (canonical, duplicates).
        """
        sorted_cluster = sorted(cluster, key=lambda a: len(a["name"]), reverse=True)
        return sorted_cluster[0], sorted_cluster[1:]
