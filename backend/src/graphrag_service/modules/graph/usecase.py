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
from graphrag_service.library.parsers import (
    iter_authors,
    iter_author_paper_edges,
    iter_method_paper_edges,
    iter_paper_method_edges,
    iter_paper_task_edges,
    load_json,
)
from graphrag_service.modules.graph.author_ingestion import (
    run_entity_resolution, prepare_author_nodes, prepare_coauthor_edges,
)

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

        # Phase 3: USES_METHOD + ADDRESSES_TASK from papers.json
        logger.info("Ingesting USES_METHOD + ADDRESSES_TASK relationships...")

        uses_method_batch: list[dict] = []
        um_total = 0
        for edge in tqdm(
            iter_paper_method_edges(papers_data, max_papers=settings.MAX_PAPERS),
            desc="USES_METHOD",
        ):
            uses_method_batch.append(edge)
            if len(uses_method_batch) >= batch_size:
                um_total += self.node_repo.batch_merge_uses_method(uses_method_batch)
                uses_method_batch = []
        um_total += self.node_repo.batch_merge_uses_method(uses_method_batch)
        logger.info(f"USES_METHOD: {um_total} edges")

        addresses_task_batch: list[dict] = []
        at_total = 0
        for edge in tqdm(
            iter_paper_task_edges(papers_data, max_papers=settings.MAX_PAPERS),
            desc="ADDRESSES_TASK",
        ):
            addresses_task_batch.append(edge)
            if len(addresses_task_batch) >= batch_size:
                at_total += self.node_repo.batch_merge_addresses_task(addresses_task_batch)
                addresses_task_batch = []
        at_total += self.node_repo.batch_merge_addresses_task(addresses_task_batch)
        logger.info(f"ADDRESSES_TASK: {at_total} edges")

        # Phase 4: INTRODUCES_METHOD from methods.json
        logger.info("Ingesting INTRODUCES_METHOD relationships...")
        methods_data = load_json(self.service.data_dir() / "methods.json")

        introduces_batch: list[dict] = []
        im_total = 0
        for edge in tqdm(
            iter_method_paper_edges(methods_data, max_items=settings.MAX_METHODS),
            desc="INTRODUCES_METHOD",
        ):
            introduces_batch.append(edge)
            if len(introduces_batch) >= batch_size:
                im_total += self.node_repo.batch_merge_introduces_method(introduces_batch)
                introduces_batch = []
        im_total += self.node_repo.batch_merge_introduces_method(introduces_batch)
        logger.info(f"INTRODUCES_METHOD: {im_total} edges")

        logger.info("Relationships ingestion done")

    def ingest_authors(self, batch_size: int = 500) -> dict:
        """Run author extraction, entity resolution, and relationship creation."""
        data_path = GraphService.data_dir()
        data = load_json(data_path / "papers.json")

        raw_authors = list(iter_authors(data))
        logger.info("Extracted %d raw authors", len(raw_authors))

        canonical_authors, uid_mapping = run_entity_resolution(raw_authors)
        logger.info("Resolved to %d canonical authors", len(canonical_authors))

        # Batch upsert Author nodes (Author has no embedding)
        author_nodes = prepare_author_nodes(canonical_authors)
        for i in range(0, len(author_nodes), batch_size):
            batch = author_nodes[i : i + batch_size]
            self._upsert_without_embedding(Author, batch)
        logger.info("Upserted %d author nodes", len(author_nodes))

        # Create AUTHORED edges
        raw_edges = list(iter_author_paper_edges(data))
        authored_rows = []
        for edge in raw_edges:
            raw_uid = f"author:{edge['author_name'].strip().lower().replace(' ', '_')}"
            canonical_uid = uid_mapping.get(raw_uid, raw_uid)
            authored_rows.append({"auid": canonical_uid, "puid": edge["paper_uid"], "order": edge["order"]})

        authored_count = 0
        for i in range(0, len(authored_rows), batch_size):
            batch = authored_rows[i : i + batch_size]
            authored_count += self.node_repo.batch_merge_authored(batch)
        logger.info("Created %d AUTHORED edges", authored_count)

        # Create CO_AUTHORED_WITH edges
        coauthor_input = [{"author_uid": r["auid"], "paper_uid": r["puid"], "order": r["order"]} for r in authored_rows]
        coauthor_rows = prepare_coauthor_edges(coauthor_input)
        coauthor_count = 0
        for i in range(0, len(coauthor_rows), batch_size):
            batch = coauthor_rows[i : i + batch_size]
            coauthor_count += self.node_repo.batch_merge_coauthored(batch)
        logger.info("Created %d CO_AUTHORED_WITH edges", coauthor_count)

        return {"raw_authors": len(raw_authors), "canonical_authors": len(canonical_authors),
                "authored_edges": authored_count, "coauthor_edges": coauthor_count}
