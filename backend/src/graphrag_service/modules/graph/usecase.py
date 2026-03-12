"""
Graph use case orchestration layer.

Coordinates service (logic) + repository (DB).
"""

from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import Author, Dataset, Method, Paper, Task

from .checkpoint import (
    IngestCheckpoint,
    NodeTypeProgress,
    load_checkpoint,
    save_checkpoint,
)
from .repositories import GraphExploreRepository, NodeRepository, SchemaRepository
from .services import GraphService


# Map model classes to their service loader methods
NODE_MODEL_LOADERS = [
    (Paper, "load_papers"),
    (Method, "load_methods"),
    (Task, "load_tasks"),
    (Dataset, "load_datasets"),
    (Author, "load_authors"),
]


class GraphUseCase:
    """Orchestrates graph operations — coordinates service (logic) + repository (DB)."""

    def __init__(self, client: Neo4jClient):
        self._client = client
        self.service = GraphService()
        self.schema_repo = SchemaRepository(client)
        self.node_repo = NodeRepository(client)
        self.explore_repo = GraphExploreRepository(client)

    def get_schema(self) -> Tuple[List[str], List[str]]:
        """Get graph schema (labels + relationship types)."""
        return self.schema_repo.get_schema()

    def create_schema(self) -> None:
        """Create constraints and vector indexes."""
        self.schema_repo.install_schema()

    def explore(self, limit: int = 50) -> Tuple[list, list]:
        """Explore graph sample."""
        return self.explore_repo.explore(limit=limit)

    def get_stats(self) -> dict:
        """Get node/edge counts."""
        return self.explore_repo.get_stats()

    def get_node(self, uid: str) -> dict | None:
        """Get a single node by uid."""
        return self.explore_repo.get_node_by_uid(uid)

    def verify_graph(self) -> dict:
        """Run comprehensive graph integrity checks."""
        return self.explore_repo.verify_graph()

    def search_nodes(self, query: str, label: str | None = None, limit: int = 20) -> list[dict]:
        """Search nodes by name."""
        return self.explore_repo.search_nodes(query, label=label, limit=limit)

    def ingest_nodes(
        self,
        *,
        node_type: str | None = None,
        offset: int = 0,
        limit: int = 0,
        resume: bool = False,
        skip_embedded: bool = False,
        checkpoint_path: Path | None = None,
    ) -> None:
        """Ingest entities with progress tracking and resume support.

        Args:
            node_type: Only ingest this label (e.g. "Paper"). None = all.
            offset: Skip this many valid items before processing.
            limit: Process at most this many items (0 = unlimited).
            resume: If True, skip node types already marked completed in checkpoint.
            skip_embedded: If True, skip embedding for nodes that already have one.
            checkpoint_path: Override default checkpoint file path.
        """
        settings = get_settings()
        batch_size = settings.INGEST_BATCH_SIZE

        checkpoint = load_checkpoint(checkpoint_path) if resume else IngestCheckpoint()

        loaders = NODE_MODEL_LOADERS
        if node_type:
            loaders = [
                (m, ln) for m, ln in NODE_MODEL_LOADERS if m.__label__ == node_type
            ]
            if not loaders:
                valid = [m.__label__ for m, _ in NODE_MODEL_LOADERS]
                raise ValueError(
                    f"Unknown node type '{node_type}'. Valid: {', '.join(valid)}"
                )

        embedded_cache: dict[str, set[str]] = {}

        for model, loader_name in loaders:
            label = model.__label__
            progress = checkpoint.get_or_create(label)
            progress.validate_consistency(batch_size)

            if resume and progress.completed:
                logger.info(f"Skipping {label} — already completed in checkpoint")
                continue

            if skip_embedded:
                embedded_cache[label] = self.node_repo.get_embedded_uids(label)
                logger.info(
                    f"{label}: {len(embedded_cache[label])} nodes already embedded"
                )

            # When resuming an incomplete type, continue from where we left off
            effective_offset = offset
            if resume and progress.total_parsed > 0 and not progress.completed:
                effective_offset = offset + progress.total_parsed
                logger.info(
                    f"{label}: resuming from item {effective_offset} "
                    f"({progress.total_parsed} already processed)"
                )

            loader = getattr(self.service, loader_name)
            logger.info(f"Ingesting {label}s (offset={effective_offset}, limit={limit})...")

            batch: list[dict] = []
            for node in tqdm(loader(offset=effective_offset, limit=limit), desc=label):
                batch.append(node)
                if len(batch) == batch_size:
                    self._process_batch(
                        model, batch, skip_embedded, embedded_cache.get(label, set()),
                        progress,
                    )
                    save_checkpoint(checkpoint, checkpoint_path)
                    batch = []

            if batch:
                self._process_batch(
                    model, batch, skip_embedded, embedded_cache.get(label, set()),
                    progress,
                )
                save_checkpoint(checkpoint, checkpoint_path)

            progress.mark_completed()
            save_checkpoint(checkpoint, checkpoint_path)
            logger.info(
                f"{label} done — {progress.total_upserted} upserted, "
                f"{progress.skipped_existing} skipped"
            )

    def _process_batch(
        self,
        model: type,
        batch: list[dict],
        skip_embedded: bool,
        embedded_uids: set[str],
        progress: NodeTypeProgress,
    ) -> None:
        """Embed and upsert a single batch, optionally skipping already-embedded nodes."""
        has_embedding = "embedding" in model.defined_properties(aliases=False, rels=False)

        # Models without embedding (e.g. Author) — upsert directly, no embedding
        if not has_embedding:
            self._upsert_without_embedding(model, batch)
            progress.mark_batch(len(batch), skipped=0)
            return

        if skip_embedded:
            need_embed = [n for n in batch if n["uid"] not in embedded_uids]
            already = len(batch) - len(need_embed)
        else:
            need_embed = batch
            already = 0

        if need_embed:
            texts = self.service.prepare_embed_texts(need_embed)
            embeddings = self.service.embed_nodes(texts)
            self.node_repo.upsert_batch(model, need_embed, embeddings)

        # Upsert nodes that already have embeddings (without re-embedding)
        skip_nodes = [n for n in batch if n["uid"] in embedded_uids] if skip_embedded else []
        if skip_nodes:
            # Use zero vectors as placeholder — the MERGE won't overwrite existing embedding
            # because _get_upsert_cypher sets all props including embedding.
            # Instead, upsert without embedding by using a separate query.
            self._upsert_without_embedding(model, skip_nodes)

        progress.mark_batch(len(batch), skipped=already)

    def _upsert_without_embedding(
        self, model: type, nodes: list[dict]
    ) -> None:
        """Upsert nodes without overwriting their existing embedding."""
        label = model.__label__
        props = [
            k for k, v in model.defined_properties(aliases=False, rels=False).items()
            if k != "embedding"
        ]
        set_parts = [f"n.{p} = row.{p}" for p in props]
        set_clause = ", ".join(set_parts)
        cypher = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{uid: row.uid}}) "
            f"SET {set_clause}"
        )
        self._client.run_query(cypher, {"rows": nodes})

    def ingest_relationships(self) -> None:
        """Ingest relationships using batched UNWIND queries for performance."""
        from graphrag_service.library.parsers import iter_author_paper_edges, load_json

        settings = get_settings()
        batch_size = settings.INGEST_BATCH_SIZE

        # Phase 1: USED_FOR + EVALUATED_ON from evaluations.json
        logger.info("Ingesting USED_FOR + EVALUATED_ON relationships...")
        evals = self.service.load_evaluations()

        used_for_batch: list[dict] = []
        eval_on_batch: list[dict] = []
        uf_total = 0
        eo_total = 0

        for ev in tqdm(evals, desc="USED_FOR + EVALUATED_ON"):
            task_name = ev.get("task", "")
            if not task_name:
                continue

            for ds_entry in ev.get("datasets", []):
                dataset_name = ds_entry.get("dataset", "")
                if not dataset_name:
                    continue

                used_for_batch.append({"dname": dataset_name, "tname": task_name})
                if len(used_for_batch) >= batch_size:
                    uf_total += self.node_repo.batch_merge_used_for(used_for_batch)
                    used_for_batch = []

                for row in (ds_entry.get("sota", {}).get("rows", []))[:5]:
                    method_name = row.get("model_name", "")
                    if not method_name:
                        continue
                    metrics = row.get("metrics", {})
                    for metric_name, metric_value in metrics.items():
                        eval_on_batch.append({
                            "mname": method_name,
                            "dname": dataset_name,
                            "metric": metric_name,
                            "score": str(metric_value),
                        })
                        if len(eval_on_batch) >= batch_size:
                            eo_total += self.node_repo.batch_merge_evaluated_on(eval_on_batch)
                            eval_on_batch = []

        # Flush remaining
        uf_total += self.node_repo.batch_merge_used_for(used_for_batch)
        eo_total += self.node_repo.batch_merge_evaluated_on(eval_on_batch)
        logger.info(f"USED_FOR: {uf_total} edges, EVALUATED_ON: {eo_total} edges")

        # Phase 2: AUTHORED from papers.json
        logger.info("Ingesting AUTHORED relationships...")
        papers_data = load_json(self.service.data_dir() / "papers.json")
        edges = iter_author_paper_edges(papers_data, max_papers=settings.MAX_PAPERS)

        authored_batch: list[dict] = []
        auth_total = 0

        for edge in tqdm(edges, desc="AUTHORED"):
            author_uid = f"author:{edge['author_name'].lower().replace(' ', '_')}"
            authored_batch.append({
                "auid": author_uid,
                "puid": edge["paper_uid"],
                "order": edge["order"],
            })
            if len(authored_batch) >= batch_size:
                auth_total += self.node_repo.batch_merge_authored(authored_batch)
                authored_batch = []

        auth_total += self.node_repo.batch_merge_authored(authored_batch)
        logger.info(f"AUTHORED: {auth_total} edges")
        logger.info("Relationships ingestion done")
