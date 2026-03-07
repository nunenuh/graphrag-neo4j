"""
Graph use case orchestration layer.

Coordinates service (logic) + repository (DB).
"""

from typing import List, Tuple

from tqdm import tqdm

from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import Dataset, Method, Paper, Task

from .repositories import GraphExploreRepository, NodeRepository, SchemaRepository
from .services import GraphService

logger = get_logger(__name__)

# Map model classes to their service loader methods
NODE_MODEL_LOADERS = [
    (Paper, "load_papers"),
    (Method, "load_methods"),
    (Task, "load_tasks"),
    (Dataset, "load_datasets"),
]


class GraphUseCase:
    """Orchestrates graph operations — coordinates service (logic) + repository (DB)."""

    def __init__(self, client: Neo4jClient):
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

    def search_nodes(self, query: str, label: str | None = None, limit: int = 20) -> list[dict]:
        """Search nodes by name."""
        return self.explore_repo.search_nodes(query, label=label, limit=limit)

    def ingest_nodes(self) -> None:
        """Ingest all entities: service parses data + embeds, repository writes to DB."""
        settings = get_settings()
        batch_size = settings.INGEST_BATCH_SIZE

        for model, loader_name in NODE_MODEL_LOADERS:
            loader = getattr(self.service, loader_name)
            logger.info(f"Ingesting {model.__label__}s...")
            batch: list[dict] = []
            for node in tqdm(loader(), desc=model.__label__):
                batch.append(node)
                if len(batch) == batch_size:
                    texts = self.service.prepare_embed_texts(batch)
                    embeddings = self.service.embed_nodes(texts)
                    self.node_repo.upsert_batch(model, batch, embeddings)
                    batch = []
            if batch:
                texts = self.service.prepare_embed_texts(batch)
                embeddings = self.service.embed_nodes(texts)
                self.node_repo.upsert_batch(model, batch, embeddings)
            logger.info(f"{model.__label__} ingestion done")

    def ingest_relationships(self) -> None:
        """Ingest relationships: service loads data, repository writes to DB."""
        logger.info("Ingesting relationships...")
        evals = self.service.load_evaluations()

        for ev in tqdm(evals, desc="Relationships"):
            task_name = ev.get("task", "")
            if not task_name:
                continue

            for ds_entry in ev.get("datasets", []):
                dataset_name = ds_entry.get("dataset", "")
                if not dataset_name:
                    continue

                self.node_repo.merge_used_for(dataset_name, task_name)

                for row in (ds_entry.get("sota", {}).get("rows", []))[:5]:
                    method_name = row.get("model_name", "")
                    if not method_name:
                        continue
                    metrics = row.get("metrics", {})
                    for metric_name, metric_value in metrics.items():
                        self.node_repo.merge_evaluated_on(
                            method_name=method_name,
                            dataset_name=dataset_name,
                            metric=metric_name,
                            score=str(metric_value),
                        )
        logger.info("Relationships ingestion done")
