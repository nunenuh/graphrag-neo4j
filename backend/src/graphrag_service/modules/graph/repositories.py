"""
Graph module repositories — encapsulate all Neo4j Cypher queries.
"""

from typing import List, Tuple

from neomodel import StructuredNode

from loguru import logger

from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import ALL_NODE_MODELS

from graphrag_service.shared.exceptions import RepositoryException


EXPLORE_QUERY = "MATCH (a)-[r]->(b) RETURN a, type(r) AS rel, b LIMIT $limit"

# Allowlist for label names — prevents Cypher injection via f-string interpolation
VALID_LABELS: frozenset[str] = frozenset(m.__label__ for m in ALL_NODE_MODELS)


def _validate_label(label: str) -> str:
    """Validate a label against the allowlist. Raises ValueError if invalid."""
    if label not in VALID_LABELS:
        raise ValueError(f"Invalid label: '{label}'. Must be one of: {', '.join(sorted(VALID_LABELS))}")
    return label


def _validate_rel_type(rel_type: str) -> str:
    """Validate a relationship type name contains only safe characters."""
    import re
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", rel_type):
        raise ValueError(f"Invalid relationship type: '{rel_type}'")
    return rel_type

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
            raise RepositoryException(f"Failed to get labels: {e}") from e

    def get_relationship_types(self) -> List[str]:
        try:
            rows = self._client.run_query(
                "CALL db.relationshipTypes() YIELD relationshipType "
                "RETURN collect(relationshipType) AS r"
            )
            return rows[0]["r"] if rows else []
        except Exception as e:
            raise RepositoryException(f"Failed to get relationship types: {e}") from e

    def get_schema(self) -> Tuple[List[str], List[str]]:
        return self.get_labels(), self.get_relationship_types()


class NodeRepository:
    """Encapsulates node upsert and relationship MERGE queries."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def get_embedded_uids(self, label: str) -> set[str]:
        """Return UIDs of nodes that already have an embedding vector."""
        validated = _validate_label(label)
        try:
            rows = self._client.run_query(
                f"MATCH (n:{validated}) WHERE n.embedding IS NOT NULL "
                "RETURN collect(n.uid) AS uids"
            )
            return set(rows[0]["uids"]) if rows else set()
        except Exception as e:
            raise RepositoryException(
                f"Failed to get embedded UIDs for {label}: {e}"
            ) from e

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
            raise RepositoryException(f"Failed to upsert {model.__label__} batch: {e}") from e

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
            raise RepositoryException(f"Failed to explore graph: {e}") from e

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

    def get_stats(self) -> dict:
        """Get node/edge counts per label."""
        counts: dict[str, int] = {}
        try:
            for model in ALL_NODE_MODELS:
                label = _validate_label(model.__label__)
                rows = self._client.run_query(
                    f"MATCH (n:{label}) RETURN count(n) AS c"
                )
                counts[label] = rows[0]["c"] if rows else 0
        except Exception as e:
            raise RepositoryException(f"Failed to get node counts: {e}") from e

        edge_counts: dict[str, int] = {}
        try:
            rel_rows = self._client.run_query(
                "CALL db.relationshipTypes() YIELD relationshipType AS t "
                "RETURN t"
            )
            for row in rel_rows:
                t = _validate_rel_type(row["t"])
                cnt_rows = self._client.run_query(
                    f"MATCH ()-[r:{t}]->() RETURN count(r) AS c"
                )
                edge_counts[t] = cnt_rows[0]["c"] if cnt_rows else 0
        except Exception as e:
            raise RepositoryException(f"Failed to get edge counts: {e}") from e

        total_nodes = sum(counts.values())
        total_edges = sum(edge_counts.values())

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_counts": counts,
            "edge_counts": edge_counts,
        }

    def get_node_by_uid(self, uid: str) -> dict | None:
        """Get a single node by uid with its label and relationships."""
        try:
            rows = self._client.run_query(
                "MATCH (n {uid: $uid}) "
                "OPTIONAL MATCH (n)-[r]->(m) "
                "OPTIONAL MATCH (p)-[r2]->(n) "
                "RETURN n, labels(n)[0] AS label, "
                "collect(DISTINCT {to: m.uid, type: type(r)}) AS outgoing, "
                "collect(DISTINCT {from: p.uid, type: type(r2)}) AS incoming",
                {"uid": uid},
            )
        except Exception as e:
            raise RepositoryException(f"Failed to get node {uid}: {e}") from e

        if not rows:
            return None

        row = rows[0]
        node = row["n"]
        if node is None:
            return None

        props = {k: v for k, v in dict(node).items() if k != "embedding"}
        outgoing = [e for e in row["outgoing"] if e.get("to") and e.get("type")]
        incoming = [e for e in row["incoming"] if e.get("from") and e.get("type")]

        return {
            "uid": props.get("uid", uid),
            "label": row["label"],
            "properties": props,
            "outgoing": outgoing,
            "incoming": incoming,
        }

    def search_nodes(
        self, query: str, label: str | None = None, limit: int = 20
    ) -> list[dict]:
        """Search nodes by name (case-insensitive contains)."""
        if label:
            validated_label = _validate_label(label)
            cypher = (
                f"MATCH (n:{validated_label}) WHERE toLower(n.name) CONTAINS toLower($q) "
                "RETURN n, labels(n)[0] AS label LIMIT $limit"
            )
        else:
            cypher = (
                "MATCH (n) WHERE n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($q) "
                "RETURN n, labels(n)[0] AS label LIMIT $limit"
            )

        try:
            rows = self._client.run_query(cypher, {"q": query, "limit": limit})
        except Exception as e:
            raise RepositoryException(f"Node search failed: {e}") from e

        results = []
        for row in rows:
            props = {k: v for k, v in dict(row["n"]).items() if k != "embedding"}
            results.append({
                "uid": props.get("uid", ""),
                "label": row["label"],
                "name": props.get("name", ""),
                "properties": props,
            })
        return results
