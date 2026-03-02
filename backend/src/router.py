import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from library.rag.retriever import retrieve
from library.rag.generator import generate_answer
from dbase.neo4j.client import Neo4jClient
from core.config import settings

router = APIRouter(prefix="/api")


def get_neo4j_client() -> Neo4jClient:
    return Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


class QueryRequest(BaseModel):
    question: str


class NodeOut(BaseModel):
    id: str
    label: str
    name: str
    score: float | None = None


class EdgeOut(BaseModel):
    from_id: str
    to_id: str
    type: str
    properties: dict = {}


class QueryResponse(BaseModel):
    answer: str
    seed_nodes: list[NodeOut]
    nodes: list[dict]
    edges: list[EdgeOut]
    cypher_used: str
    latency_ms: int


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, client: Neo4jClient = Depends(get_neo4j_client)):
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")
    t0 = time.time()
    sg = retrieve(client, req.question)
    answer = generate_answer(req.question, sg)
    return QueryResponse(
        answer=answer,
        seed_nodes=[NodeOut(id=s.id, label=s.label, name=s.name, score=s.score)
                    for s in sg.seed_nodes],
        nodes=sg.nodes,
        edges=[EdgeOut(from_id=e.from_id, to_id=e.to_id,
                       type=e.type, properties=e.properties)
               for e in sg.edges],
        cypher_used=sg.cypher_used,
        latency_ms=int((time.time() - t0) * 1000),
    )


@router.get("/graph/schema")
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    labels = client.run_query("CALL db.labels() YIELD label RETURN collect(label) AS l")
    rels = client.run_query(
        "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS r"
    )
    return {
        "node_labels":        labels[0]["l"] if labels else [],
        "relationship_types": rels[0]["r"]   if rels   else [],
    }


@router.get("/graph/explore")
async def explore(limit: int = 50, client: Neo4jClient = Depends(get_neo4j_client)):
    rows = client.run_query("""
        MATCH (a)-[r]->(b)
        RETURN a, type(r) AS rel, b LIMIT $limit
    """, {"limit": limit})
    nodes, edges = {}, []
    for row in rows:
        for n in [row["a"], row["b"]]:
            d = {k: v for k, v in dict(n).items() if k != "embedding"}
            nid = d.get("id", d.get("name", ""))
            nodes[nid] = {**d, "label": list(n.labels)[0]}
        edges.append({"from": dict(row["a"]).get("id", ""),
                      "to":   dict(row["b"]).get("id", ""),
                      "type": row["rel"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@router.get("/health")
async def health(client: Neo4jClient = Depends(get_neo4j_client)):
    return {"status": "ok", "neo4j": "connected" if client.verify_connection() else "error"}
