"""
RAG module repositories — vector search (neomodel VectorFilter) and traversal.
"""

from dataclasses import dataclass, field

from neomodel import StructuredNode
from neomodel.semantic_filters import VectorFilter

from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import Dataset, Method, Paper, Task
from graphrag_service.shared.exceptions import RepositoryException

logger = get_logger(__name__)

# Models to search across
SEARCH_MODELS: list[type[StructuredNode]] = [Paper, Method, Task, Dataset]

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
    """Vector similarity search using neomodel VectorFilter."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def search(
        self, vec: list[float], model: type[StructuredNode], k: int
    ) -> list[VectorSearchResult]:
        """Search a single neomodel node class by vector similarity."""
        label = model.__label__
        try:
            hits = model.nodes.filter(
                vector_filter=VectorFilter(
                    topk=k,
                    vector_attribute_name="embedding",
                    candidate_vector=vec,
                )
            ).all()
        except Exception as e:
            raise RepositoryException(f"Vector search failed on {label}: {e}")

        results = []
        for item in hits:
            node, score = item if isinstance(item, tuple) else (item, 0.0)

            props = {}
            for prop_name in model.defined_properties(aliases=False, rels=False):
                if prop_name != "embedding":
                    val = getattr(node, prop_name, None)
                    if val is not None:
                        props[prop_name] = val

            results.append(
                VectorSearchResult(
                    id=node.uid,
                    label=label,
                    name=getattr(node, "name", None) or getattr(node, "title", "") or "",
                    score=score,
                    properties=props,
                )
            )
        return results

    def search_all(self, vec: list[float], k: int) -> list[VectorSearchResult]:
        """Search across all node models and return top-k overall."""
        all_results: list[VectorSearchResult] = []
        for model in SEARCH_MODELS:
            all_results.extend(self.search(vec, model, k))
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
