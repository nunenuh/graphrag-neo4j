"""
RAG module repositories — vector search (Cypher) and graph traversal.
"""

from dataclasses import dataclass, field

from loguru import logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException


# Labels to search across
SEARCH_LABELS: list[str] = ["Paper", "Method", "Task", "Dataset"]

TRAVERSE_QUERY = """
    MATCH (seed) WHERE seed.uid IN $ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN seed, labels(seed)[0] AS seed_label,
           collect(DISTINCT {from: seed.uid, to: n1.uid, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT {node: n1, label: labels(n1)[0]}) AS nodes1,
           collect(DISTINCT {from: n1.uid,  to: n2.uid, type: type(r2), props: properties(r2)}) AS e2,
           collect(DISTINCT {node: n2, label: labels(n2)[0]}) AS nodes2
"""


@dataclass(frozen=True)
class VectorSearchResult:
    id: str
    label: str
    name: str
    score: float
    properties: dict = field(default_factory=dict)


class VectorSearchRepository:
    """Vector similarity search using raw Cypher db.index.vector.queryNodes."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def search(self, vec: list[float], label: str, k: int) -> list[VectorSearchResult]:
        """Search a single label by vector similarity via Cypher."""
        index_name = f"vector_index_{label}_embedding"
        cypher = (
            "CALL db.index.vector.queryNodes($index, $k, $vec) "
            "YIELD node, score "
            "RETURN node, score, labels(node)[0] AS label"
        )
        try:
            rows = self._client.run_query(cypher, {"index": index_name, "k": k, "vec": vec})
            logger.bind(label=label, index=index_name, results=len(rows)).debug("vector_search.label")
        except Exception as e:
            logger.bind(label=label, error=str(e)).error("vector_search.failed")
            raise RepositoryException(f"Vector search failed on {label}: {e}") from e

        results = []
        for row in rows:
            node = row["node"]
            props = {k: v for k, v in dict(node).items() if k != "embedding"}
            results.append(
                VectorSearchResult(
                    id=props.get("uid", ""),
                    label=row["label"],
                    name=props.get("name") or props.get("title", ""),
                    score=row["score"],
                    properties=props,
                )
            )
        return results

    def search_all(self, vec: list[float], k: int) -> list[VectorSearchResult]:
        """Search across all node labels and return top-k overall."""
        all_results: list[VectorSearchResult] = []
        for label in SEARCH_LABELS:
            all_results.extend(self.search(vec, label, k))
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:k]


class TraversalRepository:
    """Encapsulates graph traversal queries from seed nodes."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def traverse(self, node_ids: list[str]) -> tuple[dict[str, dict], list[dict]]:
        """Perform 2-hop traversal from seed node IDs.

        Returns (nodes_by_id, edges_list).
        """
        try:
            rows = self._client.run_query(TRAVERSE_QUERY, {"ids": node_ids})
            logger.bind(seed_count=len(node_ids), rows=len(rows)).debug("traversal.query_done")
        except Exception as e:
            logger.bind(seed_count=len(node_ids), error=str(e)).error("traversal.failed")
            raise RepositoryException(f"Graph traversal failed: {e}") from e

        all_nodes: dict[str, dict] = {}
        all_edges: list[dict] = []

        for r in rows:
            # Seed node (returned directly with its label)
            seed = r["seed"]
            if seed is not None:
                d = {k: v for k, v in dict(seed).items() if k != "embedding"}
                d["label"] = r.get("seed_label", "")
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                all_nodes[d.get("uid", "")] = d

            # Hop-1 and hop-2 nodes (wrapped as {node, label})
            for wrapped in (r["nodes1"] or []) + (r["nodes2"] or []):
                if wrapped is None:
                    continue
                node = wrapped.get("node") if isinstance(wrapped, dict) else wrapped
                if node is None:
                    continue
                d = {k: v for k, v in dict(node).items() if k != "embedding"}
                if isinstance(wrapped, dict) and wrapped.get("label"):
                    d["label"] = wrapped["label"]
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                all_nodes[d.get("uid", "")] = d

            for e in (r["e1"] or []) + (r["e2"] or []):
                if e.get("from") and e.get("to") and e.get("type"):
                    all_edges.append(
                        {
                            "from_id": e["from"],
                            "to_id": e["to"],
                            "type": e["type"],
                            "properties": dict(e.get("props") or {}),
                        }
                    )

        return all_nodes, all_edges
