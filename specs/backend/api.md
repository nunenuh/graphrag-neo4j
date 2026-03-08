# Backend Spec: API Layer

Files: `backend/src/graphrag_service/main.py`, `backend/src/graphrag_service/router.py`

See also: [[projects/graphrag-neo4j/docs/technical/api-spec]]

---

## Responsibility

| File | Does |
|------|------|
| `graphrag_service/main.py` | App factory (`create_app()`) — creates FastAPI app, registers CORS, mounts aggregated router |
| `graphrag_service/router.py` | Aggregates module routers under `/api/v1/{module}` |
| `graphrag_service/modules/{module}/apiv1/handler.py` | Per-module endpoint definitions |
| `graphrag_service/modules/{module}/schemas.py` | Per-module Pydantic request/response models |
| `graphrag_service/core/config.py` | `Settings` (pydantic-settings) + `get_settings()` with `lru_cache` |
| `graphrag_service/core/auth.py` | `get_api_key` dependency — X-API-Key header validation |
| `graphrag_service/core/dependencies.py` | `get_neo4j_client()` singleton, `close_neo4j_client()` |
| `graphrag_service/core/logging.py` | structlog setup via `setup_logging()`, `get_logger(__name__)` |
| `graphrag_service/dbase/neo4j/client.py` | Neo4j client using neomodel (`db.cypher_query`) |

The API layer is **thin**: validate -> delegate to `usecase` -> serialize response. No business logic in handlers.

---

## `main.py`

```python
"""
graphrag_service/main.py

FastAPI app factory. Configures CORS, registers routers, manages lifecycle.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.dependencies import close_neo4j_client
from .core.logging import setup_logging
from .router import api_router

logger = logging.getLogger(__name__)


def get_docs_path():
    """Get docs path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/docs"
    return None


def get_redoc_path():
    """Get redoc path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/redoc"
    return None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=get_docs_path(),
        redoc_url=get_redoc_path(),
        debug=settings.APP_DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
```

**Rules:**
- Settings loaded via `get_settings()` (cached with `lru_cache`) — never import a global `settings` object directly
- CORS origins come from `settings.allowed_origins` — never hardcode URLs
- Router prefix is `/api`; version prefix `/v1` is added by the aggregating router
- Swagger docs (`/docs`, `/redoc`) are disabled in production via `get_docs_path()` / `get_redoc_path()`
- No business logic in `main.py`
- Shutdown event calls `close_neo4j_client()` to cleanly close the neomodel connection
- Default port is **8005** (configured via `APP_PORT`)

---

## `router.py` — Route Aggregator

```python
"""
graphrag_service/router.py

Aggregates all module routers under versioned prefixes.
"""
from fastapi import APIRouter

from .modules.graph.apiv1.handler import router as graph_router
from .modules.health.apiv1.handler import router as health_router
from .modules.rag.apiv1.handler import router as rag_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/v1/health", tags=["Health"])
api_router.include_router(graph_router, prefix="/v1/graph", tags=["Graph"])
api_router.include_router(rag_router, prefix="/v1/rag", tags=["RAG"])
```

There is **no monolithic router** with all endpoints. Each module owns its own `apiv1/handler.py`. The aggregating `router.py` only wires them together.

---

## Endpoint Summary

| Method | Full Path | Module | Auth | Handler |
|--------|-----------|--------|------|---------|
| `GET` | `/api/v1/health/ping` | health | None | `modules/health/apiv1/handler.py` |
| `GET` | `/api/v1/health/neo4j` | health | None | `modules/health/apiv1/handler.py` |
| `GET` | `/api/v1/health/status` | health | None | `modules/health/apiv1/handler.py` |
| `GET` | `/api/v1/graph/schema` | graph | X-API-Key | `modules/graph/apiv1/handler.py` |
| `GET` | `/api/v1/graph/explore` | graph | X-API-Key | `modules/graph/apiv1/handler.py` |
| `POST` | `/api/v1/rag/query` | rag | X-API-Key | `modules/rag/apiv1/handler.py` |

---

## Pydantic Models

Models live in each module's `schemas.py` file, not in the router.

### Health Module — `modules/health/schemas.py`

```python
class PingResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str

class Neo4jPingResponse(BaseModel):
    status: str                          # "healthy" | "unhealthy"
    message: str
    response_time_ms: float
    timestamp: datetime

class ComponentHealth(BaseModel):
    name: str
    status: str                          # "healthy" | "unhealthy"
    message: str | None = None
    response_time_ms: float | None = None

class HealthStatusResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    components: list[ComponentHealth]
    uptime_seconds: float
```

### Graph Module — `modules/graph/schemas.py`

```python
class GraphSchemaResponse(BaseModel):
    node_labels: list[str]
    relationship_types: list[str]

class GraphNodeOut(BaseModel):
    id: str = ""
    label: str = "Node"
    name: str = ""
    properties: dict = Field(default_factory=dict)

class GraphEdgeOut(BaseModel):
    from_id: str
    to_id: str
    type: str

class GraphExploreResponse(BaseModel):
    nodes: list[dict]
    edges: list[GraphEdgeOut]
```

### RAG Module — `modules/rag/schemas.py`

```python
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class SeedNodeOut(BaseModel):
    id: str
    label: str       # "Paper" | "Method" | "Task" | "Dataset"
    name: str
    score: float | None = None

class EdgeOut(BaseModel):
    from_id: str
    to_id: str
    type: str
    properties: dict = Field(default_factory=dict)

class PipelineMetadata(BaseModel):
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    top_k: int
    traversal_depth: int
    seed_count: int
    node_count: int
    edge_count: int
    context_length: int
    step_timings: dict[str, float] = Field(default_factory=dict)  # step → ms

class QueryResponse(BaseModel):
    answer: str
    seed_nodes: list[SeedNodeOut]
    nodes: list[dict]
    edges: list[EdgeOut]
    cypher_used: str
    latency_ms: int
    metadata: PipelineMetadata | None = None
```

**Model Rules:**
- Use `Field(..., min_length=1)` for required non-empty strings
- Use `Field(default_factory=dict)` for optional dict fields (not `{}` as default)
- All response models are `BaseModel` — no `orm_mode`
- `label` is always the Neo4j label string: `"Paper"`, `"Method"`, `"Task"`, `"Dataset"`

---

## Module Handlers

Each module follows the pattern: handler imports a `UseCase` class, instantiates it (injecting `Neo4jClient` via `Depends(get_neo4j_client)` where needed), and delegates all logic.

### Health Handler — `modules/health/apiv1/handler.py`

```python
from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger

from ..schemas import HealthStatusResponse, Neo4jPingResponse, PingResponse
from ..usecase import HealthUseCase

router = APIRouter()
_health_usecase = HealthUseCase()

@router.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(status="ok", timestamp=datetime.now(UTC), message="pong")

@router.get("/neo4j", response_model=Neo4jPingResponse)
async def neo4j_ping():
    """Check Neo4j connectivity independently."""
    component = _health_usecase.service.check_neo4j()
    return Neo4jPingResponse(
        status=component.status,
        message=component.message or "",
        response_time_ms=component.response_time_ms or 0,
        timestamp=datetime.now(UTC),
    )

@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status():
    usecase = HealthUseCase()
    overall_status, components, uptime = usecase.get_basic_health()
    return HealthStatusResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version=get_settings().APP_VERSION,
        components=components,
        uptime_seconds=uptime,
    )
```

### Graph Handler — `modules/graph/apiv1/handler.py`

```python
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient

from ..schemas import GraphExploreResponse, GraphSchemaResponse
from ..usecase import GraphUseCase

logger = get_logger(__name__)
router = APIRouter()

@router.get("/schema", response_model=GraphSchemaResponse)
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    usecase = GraphUseCase(client)
    labels, rels = usecase.get_schema()
    return GraphSchemaResponse(node_labels=labels, relationship_types=rels)

@router.get("/explore", response_model=GraphExploreResponse)
async def explore(
    limit: int = Query(50, ge=1, le=500),
    client: Neo4jClient = Depends(get_neo4j_client),
):
    usecase = GraphUseCase(client)
    nodes, edges = usecase.explore(limit=limit)
    return GraphExploreResponse(nodes=nodes, edges=edges)
```

### RAG Handler — `modules/rag/apiv1/handler.py`

```python
from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient

from ..schemas import EdgeOut, PipelineMetadata, QueryRequest, QueryResponse, SeedNodeOut
from ..usecase import RAGUseCase

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, client: Neo4jClient = Depends(get_neo4j_client)):
    usecase = RAGUseCase(client)
    settings = get_settings()
    t0 = time.time()
    result = usecase.query(req.question)
    subgraph = result.get("subgraph", {})
    latency_ms = int((time.time() - t0) * 1000)

    seed_nodes_out = [SeedNodeOut(...) for s in subgraph.get("seed_nodes", [])]
    nodes_out = subgraph.get("nodes", [])
    edges_out = [EdgeOut(...) for e in subgraph.get("edges", [])]

    metadata = PipelineMetadata(
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dim=settings.EMBEDDING_DIM,
        top_k=settings.TOP_K_SEED_NODES,
        traversal_depth=settings.TRAVERSAL_DEPTH,
        seed_count=len(seed_nodes_out),
        node_count=len(nodes_out),
        edge_count=len(edges_out),
        context_length=len(result.get("context", "")),
        step_timings=result.get("step_timings", {}),
    )

    return QueryResponse(
        answer=result["answer"],
        seed_nodes=seed_nodes_out,
        nodes=nodes_out,
        edges=edges_out,
        cypher_used=subgraph.get("cypher_used", ""),
        latency_ms=latency_ms,
        metadata=metadata,
    )
```

---

## Error Handling Rules

| Scenario | HTTP Status | Error Key |
|----------|-------------|-----------|
| Empty question | 422 (auto by Pydantic `min_length=1`) | Pydantic validation error |
| Neo4j unreachable | 503 | `graph_schema_error` / `graph_explore_error` |
| OpenAI API error | 503 | `openai_error` |
| Health check failure | 503 | `health_check_failed` |
| Internal error | 500 | `internal_error` |

Error responses use a structured detail dict:

```python
raise HTTPException(
    status_code=503,
    detail={
        "error": "graph_schema_error",
        "message": str(e),
        "timestamp": datetime.now(UTC).isoformat(),
    },
)
```

**Never expose internal errors** (stack traces, Neo4j error messages, OpenAI error messages) in the HTTP response. Log them server-side with structlog, return a structured error to the client.

---

## `dbase/neo4j/client.py`

```python
"""
graphrag_service/dbase/neo4j/client.py

Neo4j client using neomodel for connection and query execution.
"""
from neomodel import db, get_config, install_all_labels

from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)


class Neo4jClient:
    """Neo4j client using neomodel for connection and query execution."""

    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        """Configure neomodel connection."""
        host = self._uri.replace("bolt://", "").replace("neo4j://", "")
        config = get_config()
        config.database_url = f"bolt://{self._user}:{self._password}@{host}"
        self._connected = True
        logger.info("Neomodel connection configured", uri=self._uri)

    def close(self) -> None:
        """Close the neomodel connection."""
        if self._connected:
            db.close_connection()
            self._connected = False
            logger.info("Neomodel connection closed")

    def verify_connection(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            db.cypher_query("RETURN 1")
            return True
        except Exception as e:
            logger.error("Neo4j connectivity check failed", error=str(e))
            return False

    def install_labels(self) -> None:
        """Install all neomodel labels, constraints, and indexes in Neo4j."""
        install_all_labels()
        logger.info("Neomodel labels installed")

    def run_query(self, cypher: str, params: dict | None = None) -> list:
        """Execute a raw Cypher query and return results as list of dicts."""
        results, meta = db.cypher_query(cypher, params or {})
        if not meta:
            return results
        return [dict(zip(meta, row)) for row in results]
```

**Neo4j Client Rules:**
- Uses **neomodel** (not the raw `neo4j` Python driver)
- All queries go through `db.cypher_query()` from neomodel
- Always parameterize queries — `$param_name`, never f-string into Cypher
- `run_query` returns `list[dict]` (column names from `meta` zipped with row values)
- `verify_connection()` for health checks
- `install_labels()` for setting up neomodel constraints/indexes
- `close()` calls `db.close_connection()` — invoked on app shutdown

---

## Dependency Injection — `core/dependencies.py`

```python
from graphrag_service.core.config import get_settings
from graphrag_service.dbase.neo4j.client import Neo4jClient

_neo4j_client: Neo4jClient | None = None

def get_neo4j_client() -> Neo4jClient:
    """Get or create Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        settings = get_settings()
        _neo4j_client = Neo4jClient(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
        )
    return _neo4j_client

def close_neo4j_client() -> None:
    """Close Neo4j client connection."""
    global _neo4j_client
    if _neo4j_client is not None:
        _neo4j_client.close()
        _neo4j_client = None
```

Handlers inject the client via `client: Neo4jClient = Depends(get_neo4j_client)`.

---

## Authentication — `core/auth.py`

```python
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from .config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="No API key provided")
    if api_key_header != get_settings().APP_X_API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API key")
    return api_key_header
```

Use as a dependency: `Depends(get_api_key)`. The API key is set via `APP_X_API_KEY` env var.

---

## Logging — `core/logging.py`

- Uses **loguru** for structured logging
- Development: colorized console output at DEBUG level
- Production: JSON output at INFO level
- Get a logger: `from loguru import logger`
- Structured context via `logger.bind(key=value).info("message")`
- Third-party loggers (uvicorn, fastapi, neo4j) set to WARNING

---

## Configuration — `core/config.py`

Key settings (loaded from env vars via `pydantic-settings`):

| Setting | Default | Description |
|---------|---------|-------------|
| `APP_NAME` | `"GraphRAG Service"` | Application name |
| `APP_HOST` | `"0.0.0.0"` | Server bind host |
| `APP_PORT` | `8005` | Server port |
| `APP_ENVIRONMENT` | `"development"` | Environment (`development`, `local`, `staging`, `production`) |
| `APP_DEBUG` | `False` | Debug mode (enables auto-reload) |
| `APP_X_API_KEY` | `"changeme"` | API key for X-API-Key auth |
| `ALLOWED_ORIGINS_STR` | `"http://localhost:3000,http://localhost:5173"` | CORS origins (comma-separated) |
| `NEO4J_URI` | `"bolt://localhost:7687"` | Neo4j bolt URI |
| `NEO4J_USER` | `"neo4j"` | Neo4j username |
| `NEO4J_PASSWORD` | `"password123"` | Neo4j password |
| `LLM_PROVIDER` | `"openai"` | LLM provider (openai\|google\|ollama\|qwen) |
| `LLM_MODEL` | `"gpt-4o-mini"` | LLM model name |
| `EMBEDDING_PROVIDER` | `"openai"` | Embedding provider (openai\|google\|ollama\|qwen) |
| `EMBEDDING_MODEL` | `"text-embedding-3-small"` | Embedding model |
| `EMBEDDING_DIM` | `1536` | Embedding dimension |
| `OPENAI_API_KEY` | `""` | OpenAI API key |
| `GOOGLE_API_KEY` | `""` | Google API key |
| `QWEN_API_KEY` | `""` | Qwen / DashScope API key |
| `QWEN_BASE_URL` | `"https://dashscope-intl.aliyuncs.com/compatible-mode/v1"` | Qwen base URL |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama base URL |
| `TOP_K_SEED_NODES` | `5` | Vector search top-k |
| `TRAVERSAL_DEPTH` | `2` | Graph traversal depth |

Access via `get_settings()` — cached with `@lru_cache()`.

---

## CORS Configuration

```python
# Allowed origins from settings
# Development: http://localhost:5173 (Vite), http://localhost:3000
# Production: set ALLOWED_ORIGINS_STR env var to your domain

ALLOWED_ORIGINS_STR=http://localhost:5173,http://localhost:3000
```

For production, set `ALLOWED_ORIGINS_STR` to the deployed frontend URL. Never use `*` in production.

---

## Docker

Docker Compose is located at `docker/docker-compose.dev.yml` (not at the repo root).
