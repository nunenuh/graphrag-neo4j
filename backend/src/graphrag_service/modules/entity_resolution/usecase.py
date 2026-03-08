"""Entity resolution use case — coordinates service + repository."""

from loguru import logger
from tqdm import tqdm

from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient

from .repositories import AuthorRepository
from .services import ERService


class ERUseCase:
    """Orchestrates entity resolution — coordinates service (logic) + repository (DB)."""

    def __init__(self, client: Neo4jClient):
        self.service = ERService()
        self.repo = AuthorRepository(client)

    def ingest_authors(self) -> int:
        """Ingest author nodes and AUTHORED relationships from PwC data.

        Returns the number of authors ingested.
        """
        settings = get_settings()
        batch_size = settings.ER_BATCH_SIZE

        # Phase 1: Ingest Author nodes
        logger.info("Ingesting Author nodes...")
        batch: list[dict] = []
        count = 0
        for author in tqdm(self.service.load_authors(), desc="Authors"):
            enriched = self.service.prepare_author_for_upsert(author)
            batch.append(enriched)
            if len(batch) >= batch_size:
                self.repo.upsert_authors_batch(batch)
                count += len(batch)
                batch = []
        if batch:
            self.repo.upsert_authors_batch(batch)
            count += len(batch)
        logger.info(f"Ingested {count} Author nodes")

        # Phase 2: Ingest AUTHORED relationships
        logger.info("Ingesting AUTHORED relationships...")
        edge_batch: list[dict] = []
        edge_count = 0
        for edge in tqdm(self.service.load_author_paper_edges(), desc="AUTHORED"):
            prepared = self.service.prepare_edge_for_merge(edge)
            edge_batch.append(prepared)
            if len(edge_batch) >= batch_size:
                self.repo.merge_authored_batch(edge_batch)
                edge_count += len(edge_batch)
                edge_batch = []
        if edge_batch:
            self.repo.merge_authored_batch(edge_batch)
            edge_count += len(edge_batch)
        logger.info(f"Ingested {edge_count} AUTHORED relationships")

        return count

    def resolve(self) -> dict:
        """Run entity resolution: blocking → scoring → clustering → merge.

        Returns summary stats of the resolution.
        """
        settings = get_settings()

        # Get all non-merged authors from DB
        authors = self.repo.get_all_authors()
        logger.info(f"Loaded {len(authors)} non-merged authors for resolution")

        # Run blocking + clustering
        clusters = self.service.resolve_blocks(
            authors,
            threshold=settings.ER_SIMILARITY_THRESHOLD,
            max_block_size=settings.ER_MAX_BLOCK_SIZE,
        )

        # Merge each cluster
        total_merged = 0
        for cluster in tqdm(clusters, desc="Merging clusters"):
            canonical, duplicates = self.service.pick_canonical(cluster)
            merged_uids = [d["uid"] for d in duplicates]
            aliases = [d["name"] for d in duplicates] + [canonical["name"]]
            self.repo.merge_authors(canonical["uid"], merged_uids, aliases)
            total_merged += len(duplicates)

        logger.info(f"Merged {total_merged} duplicate authors into {len(clusters)} canonical authors")

        return {
            "blocks_processed": len(clusters),
            "clusters_found": len(clusters),
            "authors_merged": total_merged,
        }

    def get_stats(self) -> dict:
        """Get ER statistics from the database."""
        stats = self.repo.get_stats()
        canonical = stats["total_authors"] - stats["merged_authors"]
        return {
            "total_authors": stats["total_authors"],
            "merged_authors": stats["merged_authors"],
            "canonical_authors": canonical,
            "total_authored_rels": stats["total_authored_rels"],
            "clusters_found": 0,
        }
