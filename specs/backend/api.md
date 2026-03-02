# Backend Spec: API Layer

Files: `backend/src/router.py`, `backend/src/main.py`

See also: [[projects/graphrag-neo4j/docs/technical/api-spec]]

---

## Responsibility

| File | Does |
|------|------|
| `src/router.py` | FastAPI router — endpoint definitions, request/response models, error handling |
| `src/main.py` | App factory — creates FastAPI app, registers CORS, mounts router |

The API layer is **thin**: validate → call RAG/graph layer → serialize response. No business logic here.

---

## `main.py`

```python
"""
main.py

FastAPI app factory. Configures CORS, registers routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router import router
from core.config import settings

app = FastAPI(
    title="graphrag-neo4j",
    description="Graph RAG over ML research papers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
```

**Rules:**
- CORS origins come from `settings.allowed_origins` — never hardcode URLs
- Router prefix is `/api`
- No business logic in `main.py`

---

## Pydantic Models

All request/response types are defined in `router.py` (or a separate `models.py` at `src/` root if the file grows large).

```python
from pydantic import BaseModel, Field


# --- Request ---

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")


# --- Response sub-models ---

class SeedNode(BaseModel):
    id: str
    label: str   # "Paper" | "Method" | "Task" | "Dataset"
    name: str
    score: float = Field(..., ge=0.0, le=1.0)


class GraphNode(BaseModel):
    id: str
    label: str
    name: str = ""
    title: str = ""
    description: str = ""


class GraphEdge(BaseModel):
    from_id: str
    to_id: str
    type: str
    properties: dict = Field(default_factory=dict)


# --- Main response ---

class QueryResponse(BaseModel):
    answer: str
    seed_nodes: list[SeedNode]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    cypher_used: str
    latency_ms: int


# --- Supporting responses ---

class SchemaResponse(BaseModel):
    node_labels: list[str]
    relationship_types: list[str]


class ExploreNode(BaseModel):
    id: str
    name: str
    label: str


class ExploreEdge(BaseModel):
    from_id: str
    to_id: str
    type: str


class ExploreResponse(BaseModel):
    nodes: list[ExploreNode]
    edges: list[ExploreEdge]


class HealthResponse(BaseModel):
    status: str    # "ok"
    neo4j: str     # "connected" | "error"
    version: str
```

**Model Rules:**
- Use `Field(..., min_length=1)` for required non-empty strings
- Use `Field(default_factory=dict)` for optional dict fields (not `{}` as default)
- All response models are `BaseModel` — not `orm_mode` (we're not using SQLAlchemy)
- `label` is always the Neo4j label string: `"Paper"`, `"Method"`, `"Task"`, `"Dataset"`

---

## `router.py`

```python
"""
router.py

FastAPI route definitions for graphrag-neo4j.
All business logic is delegated to library/rag/ and library/graph/ modules.
"""
import logging
import time

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from dbase.neo4j.client import Neo4jClient
from library.rag.retriever import retrieve
from library.rag.generator import generate_answer

logger = logging.getLogger(__name__)
router = APIRouter()


def get_neo4j_client() -> Neo4jClient:
    """Create a Neo4j client instance."""
    return Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


# ─────────────────────────────────────────────
# POST /api/query
# ─────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Run the Graph RAG pipeline.

    1. Embed the question
    2. Vector search for seed nodes
    3. Graph traversal from seed nodes
    4. Generate LLM answer from subgraph
    """
    start = time.time()
    client = get_neo4j_client()

    try:
        subgraph = retrieve(request.question, client)
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Graph retrieval failed")

    try:
        answer = generate_answer(
            question=request.question,
            nodes=subgraph.nodes,
            edges=subgraph.edges,
            seed_nodes=subgraph.seed_nodes,
        )
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        raise HTTPException(status_code=500, detail="Answer generation failed")

    latency_ms = int((time.time() - start) * 1000)

    return QueryResponse(
        answer=answer,
        seed_nodes=[
            SeedNode(id=sn.id, label=sn.label, name=sn.name, score=sn.score)
            for sn in subgraph.seed_nodes
        ],
        nodes=[
            GraphNode(id=n.id, label=n.label, name=n.name, title=n.title, description=n.description)
            for n in subgraph.nodes
        ],
        edges=[
            GraphEdge(from_id=e.from_id, to_id=e.to_id, type=e.type, properties=e.properties)
            for e in subgraph.edges
        ],
        cypher_used=subgraph.cypher_used,
        latency_ms=latency_ms,
    )


# ─────────────────────────────────────────────
# GET /api/graph/schema
# ─────────────────────────────────────────────

@router.get("/graph/schema", response_model=SchemaResponse)
async def graph_schema() -> SchemaResponse:
    """Return all node labels and relationship types."""
    client = get_neo4j_client()
    try:
        labels_result = client.run_query("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        rels_result = client.run_query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS types")
        return SchemaResponse(
            node_labels=labels_result[0]["labels"] if labels_result else [],
            relationship_types=rels_result[0]["types"] if rels_result else [],
        )
    except Exception as e:
        logger.error(f"Schema query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch schema")


# ─────────────────────────────────────────────
# GET /api/graph/explore
# ─────────────────────────────────────────────

@router.get("/graph/explore", response_model=ExploreResponse)
async def graph_explore(limit: int = Query(default=50, ge=1, le=200)) -> ExploreResponse:
    """Return a sample of the graph for initial visualization."""
    client = get_neo4j_client()
    cypher = """
    MATCH (a)-[r]->(b)
    RETURN
        a.id AS from_id, coalesce(a.name, a.title, a.id) AS from_name, labels(a)[0] AS from_label,
        b.id AS to_id, coalesce(b.name, b.title, b.id) AS to_name, labels(b)[0] AS to_label,
        type(r) AS rel_type
    LIMIT $limit
    """
    try:
        results = client.run_query(cypher, {"limit": limit})
    except Exception as e:
        logger.error(f"Explore query failed: {e}")
        raise HTTPException(status_code=500, detail="Graph explore failed")

    nodes_seen: dict[str, ExploreNode] = {}
    edges = []

    for row in results:
        for nid, name, label in [
            (row["from_id"], row["from_name"], row["from_label"]),
            (row["to_id"], row["to_name"], row["to_label"]),
        ]:
            if nid not in nodes_seen:
                nodes_seen[nid] = ExploreNode(id=nid, name=name, label=label)
        edges.append(ExploreEdge(from_id=row["from_id"], to_id=row["to_id"], type=row["rel_type"]))

    return ExploreResponse(nodes=list(nodes_seen.values()), edges=edges)


# ─────────────────────────────────────────────
# GET /api/health
# ─────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check — returns API status and Neo4j connectivity."""
    neo4j_status = "error"
    try:
        client = get_neo4j_client()
        client.run_query("RETURN 1")
        neo4j_status = "connected"
    except Exception as e:
        logger.warning(f"Neo4j health check failed: {e}")

    return HealthResponse(status="ok", neo4j=neo4j_status, version="0.1.0")
```

---

## Error Handling Rules

| Scenario | HTTP Status | `detail` message |
|----------|-------------|-----------------|
| Empty question | 422 (auto by Pydantic `min_length=1`) | Pydantic validation error |
| Neo4j unreachable | 500 | `"Graph retrieval failed"` |
| OpenAI API error | 500 | `"Answer generation failed"` |
| Internal error | 500 | Generic message — no stack traces in responses |

**Never expose internal errors** (stack traces, Neo4j error messages, OpenAI error messages) in the HTTP response. Log them server-side, return a generic message to the client.

---

## `dbase/neo4j/client.py`

```python
"""
dbase/neo4j/client.py

Neo4j driver wrapper. All queries go through run_query().
"""
import logging
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Thin wrapper around the Neo4j Python driver."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def run_query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """
        Execute a Cypher query and return results as a list of dicts.

        Args:
            cypher: Cypher query string (use $param_name for parameters)
            params: Query parameters (never string-interpolate values into cypher)

        Returns:
            List of result rows as dictionaries
        """
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]

    def close(self) -> None:
        """Close the driver connection."""
        self._driver.close()
```

**Neo4j Client Rules:**
- Always parameterize queries — `$param_name`, never f-string into Cypher
- `run_query` always returns `list[dict]` — never raw Record objects
- One session per query call (simple, no connection pooling needed for this project)
- `close()` called when app shuts down

---

## CORS Configuration

```python
# Allowed origins from settings
# Development: http://localhost:5173 (Vite dev server)
# Production: set ALLOWED_ORIGINS env var to your domain

ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

For production, set `ALLOWED_ORIGINS` to the deployed frontend URL. Never use `*` in production.
