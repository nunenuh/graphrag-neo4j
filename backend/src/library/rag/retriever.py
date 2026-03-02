from dataclasses import dataclass, field
from dbase.neo4j.client import Neo4jClient
from core.config import settings
from library.rag.embedder import embed_text


@dataclass
class SeedNode:
    id: str
    label: str
    name: str
    score: float
    properties: dict = field(default_factory=dict)


@dataclass
class SubgraphEdge:
    from_id: str
    to_id: str
    type: str
    properties: dict = field(default_factory=dict)


@dataclass
class RetrievedSubgraph:
    seed_nodes: list[SeedNode]
    nodes: list[dict]
    edges: list[SubgraphEdge]
    cypher_used: str


INDEXES = [
    ("paper_embeddings",   "Paper"),
    ("method_embeddings",  "Method"),
    ("task_embeddings",    "Task"),
    ("dataset_embeddings", "Dataset"),
]


def _vector_search(
    client: Neo4jClient, vec: list[float], index: str, label: str, k: int
) -> list[SeedNode]:
    rows = client.run_query(f"""
        CALL db.index.vector.queryNodes('{index}', {k}, $vec)
        YIELD node, score
        RETURN node.id AS id, node.name AS name,
               node.title AS title, score,
               properties(node) AS props
    """, {"vec": vec})
    results = []
    for r in rows:
        props = {k: v for k, v in dict(r["props"]).items() if k != "embedding"}
        results.append(SeedNode(
            id=r["id"], label=label,
            name=r["name"] or r["title"] or "",
            score=r["score"], properties=props,
        ))
    return results


def find_seed_nodes(client: Neo4jClient, question: str) -> list[SeedNode]:
    vec = embed_text(question)
    k = settings.top_k_seed_nodes
    all_seeds = []
    for index, label in INDEXES:
        all_seeds.extend(_vector_search(client, vec, index, label, k))
    all_seeds.sort(key=lambda n: n.score, reverse=True)
    return all_seeds[:k]


TRAVERSE_CYPHER = """
    MATCH (seed) WHERE seed.id IN $ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN seed,
           collect(DISTINCT {from: seed.id, to: n1.id, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT n1) AS nodes1,
           collect(DISTINCT {from: n1.id,  to: n2.id, type: type(r2), props: properties(r2)}) AS e2,
           collect(DISTINCT n2) AS nodes2
"""


def traverse_from_seeds(
    client: Neo4jClient, seeds: list[SeedNode]
) -> RetrievedSubgraph:
    rows = client.run_query(TRAVERSE_CYPHER, {"ids": [s.id for s in seeds]})
    all_nodes, all_edges = {}, []
    for r in rows:
        for n in [r["seed"]] + (r["nodes1"] or []) + (r["nodes2"] or []):
            if n is None:
                continue
            d = {k: v for k, v in dict(n).items() if k != "embedding"}
            all_nodes[d.get("id", "")] = d
        for e in (r["e1"] or []) + (r["e2"] or []):
            if e.get("from") and e.get("to") and e.get("type"):
                all_edges.append(SubgraphEdge(
                    from_id=e["from"], to_id=e["to"],
                    type=e["type"], properties=dict(e.get("props") or {}),
                ))
    return RetrievedSubgraph(
        seed_nodes=seeds,
        nodes=list(all_nodes.values()),
        edges=all_edges,
        cypher_used=TRAVERSE_CYPHER,
    )


def retrieve(client: Neo4jClient, question: str) -> RetrievedSubgraph:
    seeds = find_seed_nodes(client, question)
    return traverse_from_seeds(client, seeds)
