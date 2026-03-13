"""
RAG module repositories — vector search (Cypher) and graph traversal.
"""

from collections import Counter
from dataclasses import dataclass, field

from loguru import logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException


# Labels to search across
SEARCH_LABELS: list[str] = ["Paper", "Method", "Task", "Dataset"]

TRAVERSE_QUERY = """
    MATCH (seed) WHERE seed.uid IN $ids
    OPTIONAL MATCH (seed)-[r1]-(n1)
    OPTIONAL MATCH (n1)-[r2]-(n2)
    RETURN seed, labels(seed)[0] AS seed_label,
           collect(DISTINCT {from: startNode(r1).uid, to: endNode(r1).uid, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT {node: n1, label: labels(n1)[0]}) AS nodes1,
           collect(DISTINCT {from: startNode(r2).uid,  to: endNode(r2).uid, type: type(r2), props: properties(r2)}) AS e2,
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

    def traverse(self, node_ids: list[str]) -> tuple[dict[str, dict], list[dict], list[dict]]:
        """Perform 2-hop traversal from seed node IDs.

        Returns (nodes_by_id, edges_list, traversal_path).
        """
        try:
            rows = self._client.run_query(TRAVERSE_QUERY, {"ids": node_ids})
            logger.bind(seed_count=len(node_ids), rows=len(rows)).debug("traversal.query_done")
        except Exception as e:
            logger.bind(seed_count=len(node_ids), error=str(e)).error("traversal.failed")
            raise RepositoryException(f"Graph traversal failed: {e}") from e

        all_nodes: dict[str, dict] = {}
        all_edges: list[dict] = []

        hop0_ids: set[str] = set()
        hop1_ids: set[str] = set()
        hop2_ids: set[str] = set()
        hop0_label_counter: Counter[str] = Counter()
        hop1_label_counter: Counter[str] = Counter()
        hop2_label_counter: Counter[str] = Counter()
        hop1_edge_types: set[str] = set()
        hop2_edge_types: set[str] = set()

        for r in rows:
            # Seed node (hop 0)
            seed = r["seed"]
            if seed is not None:
                d = {k: v for k, v in dict(seed).items() if k != "embedding"}
                d["label"] = r.get("seed_label", "")
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                uid = d.get("uid", "")
                all_nodes[uid] = d
                hop0_ids.add(uid)
                if d["label"]:
                    hop0_label_counter[d["label"]] += 1

            # Hop-1 nodes
            for wrapped in r["nodes1"] or []:
                if wrapped is None:
                    continue
                node = wrapped.get("node") if isinstance(wrapped, dict) else wrapped
                if node is None:
                    continue
                d = {k: v for k, v in dict(node).items() if k != "embedding"}
                if isinstance(wrapped, dict) and wrapped.get("label"):
                    d["label"] = wrapped["label"]
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                uid = d.get("uid", "")
                all_nodes[uid] = d
                if uid not in hop0_ids:
                    hop1_ids.add(uid)
                    if d.get("label"):
                        hop1_label_counter[d["label"]] += 1

            # Hop-2 nodes
            for wrapped in r["nodes2"] or []:
                if wrapped is None:
                    continue
                node = wrapped.get("node") if isinstance(wrapped, dict) else wrapped
                if node is None:
                    continue
                d = {k: v for k, v in dict(node).items() if k != "embedding"}
                if isinstance(wrapped, dict) and wrapped.get("label"):
                    d["label"] = wrapped["label"]
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                uid = d.get("uid", "")
                all_nodes[uid] = d
                if uid not in hop0_ids and uid not in hop1_ids:
                    hop2_ids.add(uid)
                    if d.get("label"):
                        hop2_label_counter[d["label"]] += 1

            # Hop-1 edges
            for e in r["e1"] or []:
                if e.get("from") and e.get("to") and e.get("type"):
                    all_edges.append({
                        "from_id": e["from"], "to_id": e["to"],
                        "type": e["type"], "properties": dict(e.get("props") or {}),
                    })
                    hop1_edge_types.add(e["type"])

            # Hop-2 edges
            for e in r["e2"] or []:
                if e.get("from") and e.get("to") and e.get("type"):
                    all_edges.append({
                        "from_id": e["from"], "to_id": e["to"],
                        "type": e["type"], "properties": dict(e.get("props") or {}),
                    })
                    hop2_edge_types.add(e["type"])

        # Build traversal path summary with human-friendly descriptions
        def _label_summary(counter: Counter[str]) -> str:
            """Format counter as '3 Papers, 2 Methods'."""
            parts = [f"{count} {label}{'s' if count > 1 else ''}" for label, count in counter.most_common()]
            return ", ".join(parts)

        EDGE_LABELS = {
            "AUTHORED": "authorship",
            "USES_METHOD": "method usage",
            "EVALUATED_ON": "evaluation",
            "USED_FOR": "task application",
            "CITES": "citations",
        }

        def _edge_summary(edge_types: set[str]) -> str:
            """Translate edge types to plain English."""
            labels = [EDGE_LABELS.get(t, t.lower().replace("_", " ")) for t in sorted(edge_types)]
            return " and ".join(labels) if len(labels) <= 2 else ", ".join(labels[:-1]) + f", and {labels[-1]}"

        seed_desc = _label_summary(hop0_label_counter) if hop0_label_counter else "nodes"
        traversal_path: list[dict] = [{
            "hop": 0,
            "node_count": len(hop0_ids),
            "node_labels": sorted(hop0_label_counter.keys()),
            "label_counts": dict(hop0_label_counter),
            "edge_types": [],
            "description": f"Found {seed_desc} matching your query",
        }]
        if hop1_ids:
            traversal_path.append({
                "hop": 1,
                "node_count": len(hop1_ids),
                "node_labels": sorted(hop1_label_counter.keys()),
                "label_counts": dict(hop1_label_counter),
                "edge_types": sorted(hop1_edge_types),
                "description": f"Discovered {_label_summary(hop1_label_counter)} through {_edge_summary(hop1_edge_types)}",
            })
        if hop2_ids:
            traversal_path.append({
                "hop": 2,
                "node_count": len(hop2_ids),
                "node_labels": sorted(hop2_label_counter.keys()),
                "label_counts": dict(hop2_label_counter),
                "edge_types": sorted(hop2_edge_types),
                "description": f"Expanded to {_label_summary(hop2_label_counter)} via {_edge_summary(hop2_edge_types)}",
            })

        return all_nodes, all_edges, traversal_path
