"""
RAG module repositories — vector search (Cypher) and graph traversal.
"""

from dataclasses import dataclass, field

from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException

logger = get_logger(__name__)

# Labels to search across
SEARCH_LABELS: list[str] = ["Paper", "Method", "Task", "Dataset"]

TRAVERSE_QUERY = """
    MATCH (seed) WHERE seed.uid IN $ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN seed,
           collect(DISTINCT {from: seed.uid, to: n1.uid, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT n1) AS nodes1,
           collect(DISTINCT {from: n1.uid,  to: n2.uid, type: type(r2), props: properties(r2)}) AS e2,
           collect(DISTINCT n2) AS nodes2
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
        except Exception as e:
            raise RepositoryException(f"Vector search failed on {label}: {e}")

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
        except Exception as e:
            raise RepositoryException(f"Graph traversal failed: {e}")

        all_nodes: dict[str, dict] = {}
        all_edges: list[dict] = []

        for r in rows:
            for n in [r["seed"]] + (r["nodes1"] or []) + (r["nodes2"] or []):
                if n is None:
                    continue
                d = {key: val for key, val in dict(n).items() if key != "embedding"}
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
