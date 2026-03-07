---
created: 2026-03-02
source: https://raw.githubusercontent.com/nunenuh/sdd-python-service/refs/heads/main/specs/conventions/03-module-structure.md
---

# Python Module Structure Conventions

> **Project Mapping**: In `graphrag-neo4j`, all Python source lives in `backend/src/graphrag_service/`.
> Feature modules live in `backend/src/graphrag_service/modules/{name}/` following the Handler -> UseCase -> Service -> Repository pattern.
> Pure reusable logic lives in `backend/src/graphrag_service/library/` — reusable building blocks that can use frameworks/libraries but are not tied to specific modules or DB models.
> Cross-module shared services and repositories live in `backend/src/graphrag_service/shared/`.

---

## Layered Architecture

The project follows a strict layered architecture where each layer has a single responsibility and a clear dependency direction:

```
Handler/CLI  →  UseCase  →  Service  →  Library
                         →  Repository
```

### Layer Responsibilities

| Layer | Responsibility | Depends On | Never Depends On |
|-------|---------------|------------|-----------------|
| **Handler/CLI** | IO only — parse request, format response | UseCase | Service, Repository, Library, DB |
| **UseCase** | High-level orchestration (what to do) | Service + Repository | Library, DB |
| **Service** | Detailed business logic (how to do it) | Library only | Repository, DB |
| **Library** | Reusable functions/classes (building blocks) | Can use frameworks (OpenAI, etc.) | Module-specific code, DB models |
| **Repository** | DB/model operations wrapper | Neo4jClient, neomodel | Service, Library |

### Detail Gradient

Each layer gets progressively more specific:

| Layer | Example |
|-------|---------|
| **UseCase** | "ingest the graph data" — calls service.parse() then repo.upsert() |
| **Service** | "parse papers with embeddings" — calls library.parse_paper(), library.embed() |
| **Library** | "clean this text, embed via LangChain, run LangGraph pipeline" — reusable, can use frameworks |
| **Repository** | "MERGE this node in Neo4j" — wraps neomodel operations |

### Key Rules

1. **Service never touches the DB** — it only orchestrates library calls
2. **UseCase is the glue** between service (logic) and repository (data)
3. **Library is reusable** — can use frameworks (OpenAI SDK, etc.) but is not tied to specific modules or DB models
4. **Handler/CLI are thin IO** — parse input, call usecase, format output
5. **Repository wraps model operations** — all DB access goes through here

---

## How These Conventions Apply to graphrag-neo4j

| General Pattern | This Project Equivalent |
|-----------------|------------------------|
| `handler.py` (HTTP) | `graphrag_service/modules/{name}/apiv1/handler.py` |
| `cli/commands.py` (CLI) | `graphrag_service/modules/{name}/cli/commands.py` |
| `usecase.py` (Orchestration) | `graphrag_service/modules/{name}/usecase.py` |
| `services.py` (Business Logic) | `graphrag_service/modules/{name}/services.py` |
| `repositories.py` (Data Access) | `graphrag_service/modules/{name}/repositories.py` |
| `schemas.py` (Validation) | `graphrag_service/modules/{name}/schemas.py` |
| Pure logic (Reusable) | `graphrag_service/library/` |
| Cross-module shared | `graphrag_service/shared/services/`, `graphrag_service/shared/repositories/` |

**Backend `src/graphrag_service/` structure:**
```
backend/src/graphrag_service/       # Python package root — imports use graphrag_service. prefix
├── __init__.py
├── main.py                         # App factory, CORS, router registration
├── router.py                       # Main API router — aggregates module routers
├── core/
│   ├── __init__.py
│   ├── config.py                   # Pydantic Settings, get_settings() function
│   ├── auth.py                     # X-API-Key dependency
│   ├── dependencies.py             # FastAPI dependency injection (get_neo4j_client, etc.)
│   └── logging.py                  # Logging setup, get_logger()
├── dbase/                          # Database layer
│   ├── __init__.py
│   └── neo4j/
│       ├── __init__.py
│       ├── client.py               # Neo4j client via neomodel (reads config internally)
│       └── models/
│           ├── __init__.py          # Re-exports: Paper, Method, Task, Dataset
│           ├── base.py              # Base neomodel StructuredNode
│           ├── nodes.py             # Node model definitions
│           └── relationships.py     # Relationship definitions
├── library/                        # Reusable logic — can use frameworks, not tied to modules/DB models
│   ├── __init__.py
│   ├── parsers.py                  # JSON data parsing (iter_papers, iter_methods, etc.)
│   ├── generator.py                # Context formatting and prompt building
│   ├── llm/                        # LangChain-based LLM abstraction (provider-agnostic)
│   │   ├── __init__.py             # Re-exports: get_chat_model, get_embeddings, generate, embed_*
│   │   ├── providers.py            # Provider factory (OpenAI, Gemini, Ollama, Qwen)
│   │   ├── chat.py                 # Chat model wrapper (generate with prompt)
│   │   └── embeddings.py           # Embedding wrapper (embed_text, embed_batch)
│   └── graph/                      # LangGraph workflow definitions
│       ├── __init__.py             # Re-exports: run_rag_pipeline
│       └── rag_pipeline.py         # RAG pipeline as LangGraph StateGraph
├── shared/                         # Cross-cutting concerns shared across modules
│   ├── __init__.py
│   ├── exceptions.py               # RepositoryException, ServiceException, etc.
│   ├── services/                   # Shared services (used by multiple modules)
│   │   └── __init__.py
│   ├── repositories/               # Shared repositories (used by multiple modules)
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── cli/                            # Top-level CLI (Typer)
│   ├── __init__.py
│   ├── base.py                     # Console helpers: print_info, print_error, etc.
│   └── main.py                     # Root Typer app, registers sub-apps
└── modules/                        # Feature modules (Handler → UseCase → Service → Repo)
    ├── __init__.py
    ├── health/
    │   ├── __init__.py
    │   ├── apiv1/
    │   │   ├── __init__.py
    │   │   └── handler.py
    │   ├── cli/
    │   │   ├── __init__.py
    │   │   └── commands.py
    │   ├── schemas.py
    │   ├── services.py
    │   └── usecase.py
    ├── graph/
    │   ├── __init__.py
    │   ├── apiv1/
    │   │   ├── __init__.py
    │   │   └── handler.py
    │   ├── cli/
    │   │   ├── __init__.py
    │   │   └── commands.py
    │   ├── schemas.py
    │   ├── services.py              # Orchestrates library calls (parsing, embedding)
    │   ├── repositories.py          # DB operations (schema install, node upsert, explore)
    │   └── usecase.py               # Orchestrates service + repository
    └── rag/
        ├── __init__.py
        ├── apiv1/
        │   ├── __init__.py
        │   └── handler.py
        ├── cli/
        │   ├── __init__.py
        │   └── commands.py
        ├── schemas.py
        ├── services.py              # Orchestrates library calls (embed, generate)
        ├── repositories.py          # DB operations (vector search, traversal)
        └── usecase.py               # Orchestrates service + repository
```

**Imports use the `graphrag_service.` prefix (the package is installed via Poetry):**
```python
from graphrag_service.core.config import get_settings      # get_settings() function, not a singleton
from graphrag_service.core.logging import get_logger        # structured logger factory
from graphrag_service.dbase.neo4j.client import Neo4jClient # Neo4j client (reads config internally)
from graphrag_service.library.parsers import iter_papers     # pure logic from library
from graphrag_service.shared.exceptions import RepositoryException
```

**Within a module, use relative imports:**
```python
from .repositories import SchemaRepository, NodeRepository  # same module
from .services import GraphService                           # same module
from ..schemas import GraphSchemaResponse                    # handler -> parent schemas
```

---

## Library Layer

The `library/` package contains **reusable building blocks** — functions and classes that can be used across multiple modules or even outside the project. Library code **can** use external frameworks and libraries (OpenAI SDK, etc.), but it should **not** be tied to specific modules, DB models, or FastAPI dependencies.

### What belongs in `library/`

| Belongs | Does NOT Belong |
|---------|----------------|
| JSON parsing functions | Module-specific orchestration |
| Text cleaning / formatting | FastAPI dependencies / handlers |
| LLM abstraction via LangChain (`library/llm/`) | neomodel DB operations |
| Embedding logic via LangChain (`library/llm/`) | Module-specific use cases |
| LangGraph workflow definitions (`library/graph/`) | Repository queries |
| Context formatting / prompt building | Code tied to a single module |
| Data transformation | Provider-specific code outside `library/llm/providers.py` |

### Example: `library/parsers.py`

```python
"""
Pure data parsing functions for PwC JSON files.
"""
import json
from pathlib import Path
from typing import Iterator


def iter_papers(data: list, max_papers: int = 5000) -> Iterator[dict]:
    """Parse raw papers JSON into clean dicts."""
    for p in data[:max_papers]:
        if not p.get("title") or not p.get("abstract"):
            continue
        yield {
            "uid": p.get("paper_url", p.get("id", "")),
            "title": p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year": p.get("published", "")[:4],
            "url": p.get("paper_url", ""),
        }


def iter_methods(data: list) -> Iterator[dict]:
    """Parse raw methods JSON into clean dicts."""
    for m in data:
        if not m.get("name"):
            continue
        yield {
            "uid": m.get("id", m["name"]),
            "name": m["name"].strip(),
            "full_name": m.get("full_name", m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }


def load_json(path: Path) -> list:
    """Load a JSON file and return its contents."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
```

### Example: `library/generator.py`

```python
"""
LLM prompt building and context formatting.
"""

SYSTEM_PROMPT = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""


def build_context(seed_nodes: list, edges: list) -> str:
    """Build a text context string from graph data for the LLM."""
    lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in seed_nodes:
        lines.append(f"  [{s['label']}] {s['name']} (score={s['score']:.2f})")
    lines.append("\nRELATIONSHIPS:")
    for e in edges[:30]:
        props = f" {e['properties']}" if e.get("properties") else ""
        lines.append(f"  ({e['from_id']}) -[{e['type']}]-> ({e['to_id']}){props}")
    return "\n".join(lines)
```

---

## Shared Layer

The `shared/` package contains cross-cutting concerns used by **multiple modules**.

### `shared/exceptions.py` — Exception hierarchy (already exists)

### `shared/services/` — Shared services

Services that are used by more than one module. For example, `EmbedderService` is used by both `graph` (for ingestion embeddings) and `rag` (for query embeddings).

```python
# shared/services/embedder.py
from graphrag_service.library.embedder import embed_text, embed_batch

class EmbedderService:
    """Shared service for embedding text using OpenAI."""
    # Orchestrates library.embedder functions
```

### `shared/repositories/` — Shared repositories

Repositories with query patterns used by multiple modules.

---

## Example Module: `graphrag_service/modules/graph/`

The `graph` module manages Neo4j schema, data ingestion, and graph exploration. It demonstrates the full layered pattern.

### File structure

```
graphrag_service/modules/graph/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py          # IO only — parse request, call usecase, format response
├── cli/
│   ├── __init__.py
│   └── commands.py          # IO only — CLI entry points
├── schemas.py               # Pydantic request/response models
├── repositories.py          # DB operations (schema install, upsert, explore queries)
├── services.py              # Business logic — orchestrates library calls
└── usecase.py               # High-level orchestration — coordinates service + repository
```

### `repositories.py` — DB operations only

```python
"""
Graph module repositories — encapsulate all Neo4j operations.
"""
from typing import List, Tuple

from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException

logger = get_logger(__name__)


class SchemaRepository:
    """Encapsulates schema-related DB operations."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def install_schema(self) -> None:
        self._client.install_labels()

    def get_labels(self) -> List[str]:
        try:
            rows = self._client.run_query(
                "CALL db.labels() YIELD label RETURN collect(label) AS l"
            )
            return rows[0]["l"] if rows else []
        except Exception as e:
            raise RepositoryException(f"Failed to get labels: {e}")


class NodeRepository:
    """Encapsulates node upsert and relationship MERGE queries."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def upsert_batch(self, model, nodes: list[dict], embeddings: list[list[float]]) -> None:
        # ... batch upsert with UNWIND/MERGE Cypher
        pass


class GraphExploreRepository:
    """Encapsulates graph exploration queries."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def explore(self, limit: int = 50) -> Tuple[list, list]:
        try:
            rows = self._client.run_query(
                "MATCH (a)-[r]->(b) RETURN a, type(r) AS rel, b LIMIT $limit",
                {"limit": limit},
            )
        except Exception as e:
            raise RepositoryException(f"Failed to explore graph: {e}")
        # ... parse nodes and edges from rows
        return list(nodes.values()), edges
```

### `services.py` — Business logic, orchestrates library calls (NO DB access)

```python
"""
Graph service — orchestrates library calls for parsing and data preparation.
"""
from pathlib import Path
from typing import Iterator

from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.library.parsers import iter_papers, iter_methods, iter_tasks, iter_datasets, load_json

logger = get_logger(__name__)


class GraphService:
    """Service for data parsing and preparation. Does NOT access the database."""

    def data_dir(self) -> Path:
        """Resolve the data directory path."""
        settings = get_settings()
        path = Path(settings.DATA_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).parent.parent.parent.parent.parent / settings.DATA_DIR

    def load_papers(self) -> Iterator[dict]:
        """Load and parse papers using library functions."""
        settings = get_settings()
        data = load_json(self.data_dir() / "papers.json")
        return iter_papers(data, max_papers=settings.MAX_PAPERS)

    def load_methods(self) -> Iterator[dict]:
        data = load_json(self.data_dir() / "methods.json")
        return iter_methods(data)

    def prepare_embed_texts(self, nodes: list[dict]) -> list[str]:
        """Prepare text strings for embedding from node dicts."""
        return [
            f"{n.get('title', n.get('name', ''))} "
            f"{n.get('abstract', n.get('description', ''))}"
            for n in nodes
        ]
```

### `usecase.py` — High-level orchestration, coordinates service + repository

```python
"""
Graph use case orchestration layer.
"""
from typing import List, Tuple

from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient

from .repositories import GraphExploreRepository, NodeRepository, SchemaRepository
from .services import GraphService

logger = get_logger(__name__)


class GraphUseCase:
    """Orchestrates graph operations — coordinates service (logic) + repository (DB)."""

    def __init__(self, client: Neo4jClient):
        self.service = GraphService()
        self.schema_repo = SchemaRepository(client)
        self.node_repo = NodeRepository(client)
        self.explore_repo = GraphExploreRepository(client)

    def get_schema(self) -> Tuple[List[str], List[str]]:
        """Get graph schema (labels + relationship types)."""
        return self.schema_repo.get_schema()

    def create_schema(self) -> None:
        """Create constraints and vector indexes."""
        self.schema_repo.install_schema()

    def explore(self, limit: int = 50) -> Tuple[list, list]:
        """Explore graph sample."""
        return self.explore_repo.explore(limit=limit)

    def ingest_nodes(self, embed_batch_fn) -> None:
        """Ingest all entities: service parses data, repository writes to DB."""
        settings = get_settings()
        batch_size = settings.INGEST_BATCH_SIZE

        iterators = [
            (Paper, self.service.load_papers()),
            (Method, self.service.load_methods()),
            # ... etc
        ]
        for model, data_iter in iterators:
            batch: list[dict] = []
            for node in data_iter:
                batch.append(node)
                if len(batch) == batch_size:
                    texts = self.service.prepare_embed_texts(batch)
                    embeddings = embed_batch_fn(texts)
                    self.node_repo.upsert_batch(model, batch, embeddings)
                    batch = []
            if batch:
                texts = self.service.prepare_embed_texts(batch)
                embeddings = embed_batch_fn(texts)
                self.node_repo.upsert_batch(model, batch, embeddings)
```

### `apiv1/handler.py` — IO only

```python
"""
Graph API endpoints — IO only, delegates to use case.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from graphrag_service.core.dependencies import get_neo4j_client
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.shared.exceptions import RepositoryException

from ..schemas import GraphExploreResponse, GraphSchemaResponse
from ..usecase import GraphUseCase

router = APIRouter()


@router.get("/schema", response_model=GraphSchemaResponse)
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    usecase = GraphUseCase(client)
    try:
        labels, rels = usecase.get_schema()
        return GraphSchemaResponse(node_labels=labels, relationship_types=rels)
    except RepositoryException as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### `cli/commands.py` — IO only

```python
"""
Graph CLI commands — IO only, delegates to use case.
"""
import typer

from graphrag_service.cli.base import print_error, print_info, print_success
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.graph.usecase import GraphUseCase


def get_graph_app() -> typer.Typer:
    app = typer.Typer(name="graph", help="Graph database management", no_args_is_help=True)

    @app.command()
    def schema():
        """Create Neo4j constraints and vector indexes."""
        print_info("Creating Neo4j schema...")
        try:
            client = get_neo4j_client()
            usecase = GraphUseCase(client)
            usecase.create_schema()
            print_success("Schema created successfully")
        except Exception as e:
            print_error(f"Schema creation failed: {e}")
            raise typer.Exit(code=1)
        finally:
            close_neo4j_client()

    return app
```

### Register in `graphrag_service/router.py`

```python
from graphrag_service.modules.graph.apiv1.handler import router as graph_router

api_router.include_router(graph_router, prefix="/v1/graph", tags=["graph"])
```

---

## Module Structure Templates

### Simple Module (No Database)

```
health/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py          # IO only
├── cli/
│   ├── __init__.py
│   └── commands.py          # IO only
├── schemas.py
├── services.py              # No repository needed
└── usecase.py               # Still required for consistency
```

### Standard Module (With Database + CLI)

```
graph/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py          # IO only
├── cli/
│   ├── __init__.py
│   └── commands.py          # IO only
├── schemas.py
├── repositories.py          # DB operations only
├── services.py              # Business logic (uses library, NOT repository)
└── usecase.py               # Orchestrates service + repository
```

---

## Import Patterns

### Within Module (Relative Imports)

```python
# handler.py -> schemas and usecase in parent
from ..schemas import GraphExploreResponse, GraphSchemaResponse
from ..usecase import GraphUseCase

# usecase.py -> services and repositories in same directory
from .services import GraphService
from .repositories import SchemaRepository, NodeRepository, GraphExploreRepository

# services.py -> library (absolute, since library is outside modules)
from graphrag_service.library.parsers import iter_papers, load_json
```

### From External Packages (Absolute Imports with `graphrag_service.` Prefix)

```python
# Core infrastructure
from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.core.dependencies import get_neo4j_client

# Database layer
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import Paper, Method, Task, Dataset

# Library (reusable logic)
from graphrag_service.library.parsers import iter_papers, iter_methods
from graphrag_service.library.generator import build_context
from graphrag_service.library.llm import embed_text, embed_batch, generate
from graphrag_service.library.llm.providers import get_chat_model, get_embeddings
from graphrag_service.library.graph import run_rag_pipeline

# Shared
from graphrag_service.shared.exceptions import RepositoryException, ServiceException
from graphrag_service.shared.services.embedder import EmbedderService

# Cross-module (absolute, not relative)
from graphrag_service.modules.rag.services import RAGService
```

### CLI Commands (Always Absolute)

```python
from graphrag_service.cli.base import console, print_error, print_info, print_success
from graphrag_service.core.config import get_settings
from graphrag_service.core.dependencies import close_neo4j_client, get_neo4j_client
from graphrag_service.modules.graph.usecase import GraphUseCase
```

---

## Configuration Access

Use the `get_settings()` function to access configuration. Do not import a `settings` singleton directly.

```python
from graphrag_service.core.config import get_settings

# Inside a function or method:
settings = get_settings()
batch_size = settings.INGEST_BATCH_SIZE
```

The `get_settings()` function is decorated with `@lru_cache()`, so it returns the same `Settings` instance on repeated calls without re-reading environment variables.

---

## Testability Benefits

The layered architecture makes each layer independently testable:

| Layer | Test Strategy | Mocks Needed |
|-------|--------------|--------------|
| **Library** | Unit tests | External SDK mocks (e.g. OpenAI) if needed |
| **Service** | Unit tests | Library mocks only |
| **Repository** | Integration tests | Neo4j test instance |
| **UseCase** | Unit tests | Service + Repository mocks |
| **Handler/CLI** | E2E / thin unit tests | UseCase mock |

---

## File Organization Checklist

When creating a new module, ensure:

- [ ] Module name follows naming conventions (lowercase, max 2 words)
- [ ] `__init__.py` exists with module docstring
- [ ] `apiv1/handler.py` exists with API endpoints (IO only)
- [ ] `apiv1/__init__.py` exists
- [ ] `schemas.py` exists with Pydantic models
- [ ] `usecase.py` exists (always required — orchestrates service + repository)
- [ ] `repositories.py` added only if database access needed
- [ ] `services.py` added only if business logic needed (uses library, NOT repository)
- [ ] `cli/commands.py` added if the module needs CLI commands (IO only)
- [ ] `cli/__init__.py` exists if `cli/` directory is present
- [ ] Reusable logic is in `library/`, not embedded in module services
- [ ] Cross-module shared services are in `shared/services/`
- [ ] Within-module imports use **relative** imports
- [ ] External imports use **absolute** imports with `graphrag_service.` prefix
- [ ] Configuration accessed via `get_settings()`, not a global singleton

## Best Practices

1. **Handlers/CLI are thin IO**: Parse input, call usecase, format output — nothing else
2. **UseCases orchestrate**: Coordinate between services (logic) and repositories (data)
3. **Services use library only**: Business logic that calls library functions, never DB
4. **Library is reusable**: Can use frameworks, but not tied to specific modules or DB models
5. **Repositories handle data access**: Database operations only, wrapped in typed exceptions
6. **Shared for cross-module**: Services/repositories used by multiple modules go in `shared/`
7. **Schemas validate**: Use Pydantic schemas for all input/output
8. **Type hints everywhere**: All functions must have type hints
9. **CLI commands**: Use Typer sub-apps in `cli/commands.py`, registered in `cli/main.py`
