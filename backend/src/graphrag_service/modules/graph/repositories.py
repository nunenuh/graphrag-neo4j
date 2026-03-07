"""
Graph module repositories — encapsulate all Neo4j Cypher queries.
"""

from typing import List, Tuple

from neomodel import StructuredNode

from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import ALL_NODE_MODELS

from graphrag_service.shared.exceptions import RepositoryException

logger = get_logger(__name__)

EXPLORE_QUERY = "MATCH (a)-[r]->(b) RETURN a, type(r) AS rel, b LIMIT $limit"

# Batch upsert Cypher templates per label
UPSERT_TEMPLATES: dict[str, str] = {}


def _get_upsert_cypher(model: type[StructuredNode]) -> str:
    """Build and cache the UNWIND/MERGE Cypher for a neomodel class."""
    label = model.__label__
    if label not in UPSERT_TEMPLATES:
        props = [
            k for k, v in model.defined_properties(aliases=False, rels=False).items()
        ]
        set_parts = [f"n.{p} = row.{p}" for p in props]
        set_parts.append("n.embedding = row.embedding")
        set_clause = ", ".join(set_parts)
        UPSERT_TEMPLATES[label] = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{uid: row.uid}}) "
            f"SET {set_clause}"
        )
    return UPSERT_TEMPLATES[label]


class SchemaRepository:
    """Encapsulates schema-related operations using neomodel."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def install_schema(self) -> None:
        """Install constraints via neomodel, then create vector indexes via Cypher."""
        self._client.install_labels()
        logger.info("Constraints and range indexes installed via neomodel")

        settings = get_settings()
        dim = settings.EMBEDDING_DIM
        for model in ALL_NODE_MODELS:
            label = model.__label__
            index_name = f"vector_index_{label}_embedding"
            cypher = (
                f"CREATE VECTOR INDEX {index_name} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.embedding) "
                f"OPTIONS {{indexConfig: {{"
                f"  `vector.dimensions`: {dim},"
                f"  `vector.similarity_function`: 'cosine'"
                f"}}}}"
            )
            self._client.run_query(cypher)
            logger.info(f"Vector index created: {index_name} (dim={dim})")

        logger.info("Schema installation complete")

    def get_labels(self) -> List[str]:
        try:
            rows = self._client.run_query(
                "CALL db.labels() YIELD label RETURN collect(label) AS l"
            )
            return rows[0]["l"] if rows else []
        except Exception as e:
            raise RepositoryException(f"Failed to get labels: {e}")

    def get_relationship_types(self) -> List[str]:
        try:
            rows = self._client.run_query(
                "CALL db.relationshipTypes() YIELD relationshipType "
                "RETURN collect(relationshipType) AS r"
            )
            return rows[0]["r"] if rows else []
        except Exception as e:
            raise RepositoryException(f"Failed to get relationship types: {e}")

    def get_schema(self) -> Tuple[List[str], List[str]]:
        return self.get_labels(), self.get_relationship_types()


class NodeRepository:
    """Encapsulates node upsert and relationship MERGE queries."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def upsert_batch(
        self,
        model: type[StructuredNode],
        nodes: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Batch upsert nodes with embeddings using raw Cypher MERGE."""
        records = [{**node, "embedding": emb} for node, emb in zip(nodes, embeddings)]
        cypher = _get_upsert_cypher(model)
        try:
            self._client.run_query(cypher, {"rows": records})
        except Exception as e:
            raise RepositoryException(f"Failed to upsert {model.__label__} batch: {e}")

    def merge_used_for(self, dataset_name: str, task_name: str) -> None:
        self._client.run_query(
            "MATCH (d:Dataset {name: $dname}) "
            "MATCH (t:Task {name: $tname}) "
            "MERGE (d)-[:USED_FOR]->(t)",
            {"dname": dataset_name, "tname": task_name},
        )

    def merge_evaluated_on(
        self,
        method_name: str,
        dataset_name: str,
        metric: str,
        score: str,
    ) -> None:
        self._client.run_query(
            "MATCH (m:Method {name: $mname}) "
            "MATCH (d:Dataset {name: $dname}) "
            "MERGE (m)-[r:EVALUATED_ON {metric: $metric}]->(d) "
            "SET r.score = $score",
            {
                "mname": method_name,
                "dname": dataset_name,
                "metric": metric,
                "score": score,
            },
        )


class GraphExploreRepository:
    """Encapsulates graph exploration queries."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def explore(self, limit: int = 50) -> Tuple[list, list]:
        try:
            rows = self._client.run_query(EXPLORE_QUERY, {"limit": limit})
        except Exception as e:
            raise RepositoryException(f"Failed to explore graph: {e}")

        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        for row in rows:
            for n in [row["a"], row["b"]]:
                props = {k: v for k, v in dict(n).items() if k != "embedding"}
                nid = props.get("uid", props.get("name", ""))
                nodes[nid] = {**props, "label": list(n.labels)[0]}
            edges.append(
                {
                    "from_id": dict(row["a"]).get("uid", ""),
                    "to_id": dict(row["b"]).get("uid", ""),
                    "type": row["rel"],
                }
            )

        return list(nodes.values()), edges
