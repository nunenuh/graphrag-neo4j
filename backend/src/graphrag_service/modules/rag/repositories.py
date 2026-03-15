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

TRAVERSE_QUERIES: dict[int, str] = {
    1: """
        MATCH (seed) WHERE seed.uid IN $ids
        OPTIONAL MATCH (seed)-[r1]-(n1)
        WITH seed, r1, n1
        ORDER BY type(r1)
        LIMIT 30
        RETURN seed, labels(seed)[0] AS seed_label,
               collect(DISTINCT {from: startNode(r1).uid, to: endNode(r1).uid, type: type(r1), props: properties(r1)}) AS e1,
               collect(DISTINCT {node: n1, label: labels(n1)[0]}) AS nodes1
    """,
    2: """
        MATCH (seed) WHERE seed.uid IN $ids
        OPTIONAL MATCH (seed)-[r1]-(n1)
        WITH seed, r1, n1
        ORDER BY type(r1)
        LIMIT 30
        WITH seed, collect(DISTINCT r1) AS rels1, collect(DISTINCT n1) AS hop1_nodes
        UNWIND hop1_nodes AS n1
        OPTIONAL MATCH (n1)-[r2]-(n2) WHERE n2.uid <> seed.uid
        WITH seed, rels1, n1, r2, n2
        ORDER BY type(r2)
        LIMIT 50
        RETURN seed, labels(seed)[0] AS seed_label,
               [r IN rels1 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e1,
               [n IN collect(DISTINCT n1) | {node: n, label: labels(n)[0]}] AS nodes1,
               collect(DISTINCT {from: startNode(r2).uid, to: endNode(r2).uid, type: type(r2), props: properties(r2)}) AS e2,
               collect(DISTINCT {node: n2, label: labels(n2)[0]}) AS nodes2
    """,
    3: """
        MATCH (seed) WHERE seed.uid IN $ids
        OPTIONAL MATCH (seed)-[r1]-(n1)
        WITH seed, r1, n1
        ORDER BY type(r1)
        LIMIT 25
        WITH seed, collect(DISTINCT r1) AS rels1, collect(DISTINCT n1) AS hop1_nodes
        UNWIND hop1_nodes AS n1
        OPTIONAL MATCH (n1)-[r2]-(n2) WHERE n2.uid <> seed.uid
        WITH seed, rels1, n1, r2, n2
        ORDER BY type(r2)
        LIMIT 40
        WITH seed, rels1, collect(DISTINCT n1) AS cn1, collect(DISTINCT r2) AS rels2, collect(DISTINCT n2) AS hop2_nodes
        UNWIND hop2_nodes AS n2
        OPTIONAL MATCH (n2)-[r3]-(n3) WHERE NOT n3.uid IN [seed.uid]
        WITH seed, rels1, cn1, rels2, n2, r3, n3
        ORDER BY type(r3)
        LIMIT 30
        RETURN seed, labels(seed)[0] AS seed_label,
               [r IN rels1 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e1,
               [n IN cn1 | {node: n, label: labels(n)[0]}] AS nodes1,
               [r IN rels2 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e2,
               [n IN collect(DISTINCT n2) | {node: n, label: labels(n)[0]}] AS nodes2,
               collect(DISTINCT {from: startNode(r3).uid, to: endNode(r3).uid, type: type(r3), props: properties(r3)}) AS e3,
               collect(DISTINCT {node: n3, label: labels(n3)[0]}) AS nodes3
    """,
    4: """
        MATCH (seed) WHERE seed.uid IN $ids
        OPTIONAL MATCH (seed)-[r1]-(n1)
        WITH seed, r1, n1
        ORDER BY type(r1)
        LIMIT 20
        WITH seed, collect(DISTINCT r1) AS rels1, collect(DISTINCT n1) AS hop1_nodes
        UNWIND hop1_nodes AS n1
        OPTIONAL MATCH (n1)-[r2]-(n2) WHERE n2.uid <> seed.uid
        WITH seed, rels1, n1, r2, n2
        ORDER BY type(r2)
        LIMIT 30
        WITH seed, rels1, collect(DISTINCT n1) AS cn1, collect(DISTINCT r2) AS rels2, collect(DISTINCT n2) AS hop2_nodes
        UNWIND hop2_nodes AS n2
        OPTIONAL MATCH (n2)-[r3]-(n3) WHERE NOT n3.uid IN [seed.uid]
        WITH seed, rels1, cn1, rels2, n2, r3, n3
        ORDER BY type(r3)
        LIMIT 25
        WITH seed, rels1, cn1, rels2, collect(DISTINCT n2) AS cn2, collect(DISTINCT r3) AS rels3, collect(DISTINCT n3) AS hop3_nodes
        UNWIND hop3_nodes AS n3
        OPTIONAL MATCH (n3)-[r4]-(n4) WHERE NOT n4.uid IN [seed.uid]
        WITH seed, rels1, cn1, rels2, cn2, rels3, n3, r4, n4
        ORDER BY type(r4)
        LIMIT 20
        RETURN seed, labels(seed)[0] AS seed_label,
               [r IN rels1 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e1,
               [n IN cn1 | {node: n, label: labels(n)[0]}] AS nodes1,
               [r IN rels2 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e2,
               [n IN cn2 | {node: n, label: labels(n)[0]}] AS nodes2,
               [r IN rels3 | {from: startNode(r).uid, to: endNode(r).uid, type: type(r), props: properties(r)}] AS e3,
               [n IN collect(DISTINCT n3) | {node: n, label: labels(n)[0]}] AS nodes3,
               collect(DISTINCT {from: startNode(r4).uid, to: endNode(r4).uid, type: type(r4), props: properties(r4)}) AS e4,
               collect(DISTINCT {node: n4, label: labels(n4)[0]}) AS nodes4
    """,
}

# Backward-compatible alias
TRAVERSE_QUERY = TRAVERSE_QUERIES[2]


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

    def traverse(self, node_ids: list[str], depth: int = 2) -> tuple[dict[str, dict], list[dict], list[dict]]:
        """Perform N-hop traversal from seed node IDs.

        Args:
            node_ids: Seed node UIDs.
            depth: Traversal depth (1-4 hops). Default 2.

        Returns (nodes_by_id, edges_list, traversal_path).
        """
        depth = max(1, min(4, depth))
        query = TRAVERSE_QUERIES.get(depth, TRAVERSE_QUERIES[2])

        try:
            rows = self._client.run_query(query, {"ids": node_ids})
            logger.bind(seed_count=len(node_ids), depth=depth, rows=len(rows)).debug("traversal.query_done")
        except Exception as e:
            logger.bind(seed_count=len(node_ids), error=str(e)).error("traversal.failed")
            raise RepositoryException(f"Graph traversal failed: {e}") from e

        all_nodes: dict[str, dict] = {}
        all_edges: list[dict] = []

        # Per-hop tracking: hop_ids[0] = seed, hop_ids[1] = hop-1, etc.
        hop_ids: list[set[str]] = [set() for _ in range(depth + 1)]
        hop_label_counters: list[Counter[str]] = [Counter() for _ in range(depth + 1)]
        hop_edge_types: list[set[str]] = [set() for _ in range(depth + 1)]

        for r in rows:
            # Seed node (hop 0)
            seed = r["seed"]
            if seed is not None:
                d = {k: v for k, v in dict(seed).items() if k != "embedding"}
                d["label"] = r.get("seed_label", "")
                d["name"] = d.get("name") or d.get("title") or d.get("uid", "")
                uid = d.get("uid", "")
                all_nodes[uid] = d
                hop_ids[0].add(uid)
                if d["label"]:
                    hop_label_counters[0][d["label"]] += 1

            # Process each hop level
            for hop in range(1, depth + 1):
                nodes_key = f"nodes{hop}"
                edges_key = f"e{hop}"

                # Nodes at this hop
                for wrapped in r.get(nodes_key) or []:
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
                    # Only count in the earliest hop where this node appears
                    already_seen = any(uid in hop_ids[h] for h in range(hop))
                    if not already_seen:
                        hop_ids[hop].add(uid)
                        if d.get("label"):
                            hop_label_counters[hop][d["label"]] += 1

                # Edges at this hop
                for e in r.get(edges_key) or []:
                    if e.get("from") and e.get("to") and e.get("type"):
                        all_edges.append({
                            "from_id": e["from"], "to_id": e["to"],
                            "type": e["type"], "properties": dict(e.get("props") or {}),
                        })
                        hop_edge_types[hop].add(e["type"])

        # Build traversal path summary with human-friendly descriptions
        def _label_summary(counter: Counter[str]) -> str:
            parts = [f"{count} {label}{'s' if count > 1 else ''}" for label, count in counter.most_common()]
            return ", ".join(parts)

        EDGE_LABELS = {
            "AUTHORED": "authorship",
            "USES_METHOD": "method usage",
            "EVALUATED_ON": "evaluation",
            "USED_FOR": "task application",
            "CITES": "citations",
            "CO_AUTHORED_WITH": "co-authorship",
        }

        def _edge_summary(edge_types: set[str]) -> str:
            labels = [EDGE_LABELS.get(t, t.lower().replace("_", " ")) for t in sorted(edge_types)]
            return " and ".join(labels) if len(labels) <= 2 else ", ".join(labels[:-1]) + f", and {labels[-1]}"

        HOP_VERBS = ["Found", "Discovered", "Expanded to", "Extended to"]

        seed_desc = _label_summary(hop_label_counters[0]) if hop_label_counters[0] else "nodes"
        traversal_path: list[dict] = [{
            "hop": 0,
            "node_count": len(hop_ids[0]),
            "node_labels": sorted(hop_label_counters[0].keys()),
            "label_counts": dict(hop_label_counters[0]),
            "edge_types": [],
            "description": f"Found {seed_desc} matching your query",
        }]
        for hop in range(1, depth + 1):
            if hop_ids[hop]:
                verb = HOP_VERBS[min(hop, len(HOP_VERBS) - 1)]
                traversal_path.append({
                    "hop": hop,
                    "node_count": len(hop_ids[hop]),
                    "node_labels": sorted(hop_label_counters[hop].keys()),
                    "label_counts": dict(hop_label_counters[hop]),
                    "edge_types": sorted(hop_edge_types[hop]),
                    "description": f"{verb} {_label_summary(hop_label_counters[hop])} through {_edge_summary(hop_edge_types[hop])}",
                })

        return all_nodes, all_edges, traversal_path
