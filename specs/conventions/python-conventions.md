---
created: 2026-03-02
source: https://raw.githubusercontent.com/nunenuh/sdd-python-service/refs/heads/main/specs/conventions/01-python-conventions.md
---

# Python Conventions

Complete Python coding conventions for `graphrag-neo4j` backend.

**Source**: Adapted from `sdd-python-service` `.cursorrules` and codebase patterns, applied to this project's structure.

---

## Code Style

### PEP 8 Compliance

- Follow PEP 8 Python style guide
- Use **Black** for code formatting (line length: 88)
- Use **isort** for import sorting (profile: black, `known_first_party = ["graphrag_service"]`)
- Use **ruff** for linting (replaces flake8)
- Use **mypy** for type checking

Configure in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["graphrag_service"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]
```

### Type Hints

- **Required** on all function signatures -- no exceptions
- Prefer built-in generic types (Python 3.11+): `list[str]`, `dict[str, float]`
- Use `Optional[T]` only for Python 3.9 compatibility; prefer `T | None` in 3.11+
- Avoid `Any` -- define proper types

```python
# Good -- Python 3.11 style
def embed_texts(texts: list[str]) -> list[list[float]]: ...
def get_node(node_id: str) -> dict | None: ...

# Good -- Optional for nullable params
def search(query: str, limit: int = 5) -> list[dict]: ...

# Bad -- No Any
def process(data: Any) -> Any: ...
```

### Async / Await

- FastAPI route handlers must be `async def`
- I/O operations (OpenAI, Neo4j) should use async when the client supports it
- `graphrag_service/dbase/neo4j/client.py` uses neomodel's sync `db.cypher_query()` -- wrap with `asyncio.to_thread()` if needed

```python
# Good -- Route handler, always async
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    result = await asyncio.to_thread(rag_service.query, request.question)
    ...

# Good -- Pure function, sync is fine
def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
```

---

## Naming Conventions

### Files & Packages

| Thing | Convention | Example |
|-------|-----------|---------|
| Modules | `snake_case.py` | `client.py`, `services.py` |
| Packages | `snake_case/` | `modules/rag/`, `modules/graph/`, `core/` |
| Test files | `test_*.py` | `test_services.py` |

### Code Elements

| Thing | Convention | Example |
|-------|-----------|---------|
| Classes | `PascalCase` | `Neo4jClient`, `QueryResponse` |
| Functions / methods | `snake_case` | `embed_text()`, `run_query()` |
| Constants | `UPPER_SNAKE_CASE` | `EMBEDDING_MODEL`, `BATCH_SIZE` |
| Variables | `snake_case` | `seed_nodes`, `query_vector` |
| Private methods | `_snake_case` | `_vector_search()`, `_attach_embeddings()` |
| Boolean variables | `is_*`, `has_*` | `is_loading`, `has_error` |

---

## Imports

Group in this order, separated by blank lines:

```python
# 1. Standard library
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterator

# 2. Third-party
import openai
import structlog
from fastapi import APIRouter, HTTPException
from neomodel import db
from pydantic import BaseModel, Field

# 3. First-party absolute (cross-subpackage)
from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.modules.rag.services import RAGService

# 4. Relative (within the same subpackage)
from .repositories import VectorSearchRepository
from .schemas import QueryRequest, QueryResponse
```

**Rules:**
- Use **absolute imports** with the `graphrag_service.` prefix when importing across subpackages
- Use **relative imports** (`from .schemas import ...`) only within the same subpackage
- Sort with `isort --profile black` (configured with `known_first_party = ["graphrag_service"]`)
- No star imports (`from module import *`)

---

## Function Design

### Size limit: 50 lines per function

If a function grows past 50 lines, extract a helper.

### Single responsibility

One function, one purpose:

```python
# Good -- Single responsibility
def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def clean_paper(raw: dict) -> dict:
    """Normalize a raw PwC paper dict into a clean entity dict."""
    title = raw.get("title", "").strip()
    url = raw.get("paper_url", "")
    return {
        "id": url.rstrip("/").split("/")[-1] if url else slugify(title),
        "title": title,
        "abstract": raw.get("abstract", "") or "",
        "url": url,
        "year": raw.get("year"),
    }

# Bad -- Mixed concerns
def process_and_save_paper(raw: dict, client: Neo4jClient) -> None:
    title = raw["title"].strip()
    # ... clean, embed, save -- all in one function
```

### Docstrings

Google-style for all public functions:

```python
def batch_embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts in batches of BATCH_SIZE.

    Args:
        texts: Texts to embed. Must be non-empty strings.

    Returns:
        List of 1536-dim embedding vectors, same order as input.

    Raises:
        openai.APIError: If any batch fails after MAX_RETRIES.
        openai.RateLimitError: If rate limit persists after retries.
    """
```

Private helpers need at minimum a one-line docstring:

```python
def _attach_embeddings(entities: list[dict], texts: list[str]) -> list[dict]:
    """Return new entity dicts with 'embedding' field attached (immutable)."""
```

---

## Immutability (CRITICAL)

**Always return new objects. Never mutate inputs.**

```python
# Good -- Immutable, returns new dict
def attach_embedding(entity: dict, embedding: list[float]) -> dict:
    return {**entity, "embedding": embedding}

# Good -- Immutable list comprehension
def attach_embeddings(entities: list[dict], embeddings: list[list[float]]) -> list[dict]:
    return [{**e, "embedding": emb} for e, emb in zip(entities, embeddings)]

# Bad -- Mutates input
def attach_embedding(entity: dict, embedding: list[float]) -> dict:
    entity["embedding"] = embedding  # side effect
    return entity
```

---

## Configuration

Use the `get_settings()` function with `@lru_cache` -- not a bare `settings = Settings()` instance.

```python
# graphrag_service/core/config.py
from functools import lru_cache
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = Field(default="GraphRAG Service")
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    OPENAI_API_KEY: str = Field(default="")
    # ...

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**Usage** -- always call `get_settings()`, never instantiate `Settings()` directly:

```python
from graphrag_service.core.config import get_settings

settings = get_settings()
uri = settings.NEO4J_URI
```

---

## Pydantic Models

### Request/Response models

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")

class SeedNode(BaseModel):
    id: str
    label: str
    name: str
    score: float = Field(..., ge=0.0, le=1.0)
```

### Rules

- `Field(...)` for required fields with constraints
- `Field(default_factory=dict)` for optional dict/list -- never `= {}` or `= []`
- `from_attributes = True` in `Config` only when converting from ORM objects
- One schema file per module if schemas are complex; inline in `handler.py` if simple

---

## Error Handling

### Always explicit, never silent

```python
from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)

# Good -- Explicit, typed exceptions, meaningful messages
try:
    result = client.run_query(cypher, params)
except Neo4jConnectionException as e:
    logger.error("Neo4j unavailable", error=str(e))
    raise HTTPException(status_code=503, detail="Database unavailable")
except Exception as e:
    logger.error("Unexpected query error", error=str(e), cypher=cypher[:100])
    raise

# Bad -- Silent swallow, never do this
try:
    result = client.run_query(cypher, params)
except:
    return []
```

### HTTP Status Codes

| Code | When |
|------|------|
| `200 OK` | Successful GET |
| `201 Created` | Successful POST that creates a resource |
| `400 Bad Request` | Validation error (empty question, bad param) |
| `401 Unauthorized` | Missing or invalid X-API-Key |
| `403 Forbidden` | Valid key, insufficient permission |
| `404 Not Found` | Resource not found |
| `422 Unprocessable Entity` | Pydantic validation failure (auto) |
| `500 Internal Server Error` | Backend crash |
| `503 Service Unavailable` | Neo4j unreachable |

### Custom exception hierarchy

```python
# graphrag_service/shared/exceptions.py
class BaseServiceException(Exception):
    """Base exception for graphrag-neo4j."""

    def __init__(self, message: str = "An error occurred") -> None:
        self.message = message
        super().__init__(self.message)

class ValidationException(BaseServiceException):
    """Validation error."""

class RepositoryException(BaseServiceException):
    """Repository/database error."""

class ServiceException(BaseServiceException):
    """Service-level error."""

class Neo4jConnectionException(RepositoryException):
    """Neo4j connection failed."""

class OpenAIException(ServiceException):
    """OpenAI API error."""
```

---

## Logging

Use **structlog** via `graphrag_service.core.logging`. Configure via `APP_ENVIRONMENT` env var.

```python
from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)  # Module-level logger

# Structured context via keyword arguments
logger.info("Batch embedded", batch=i, total=total_batches, size=len(batch))
logger.warning("Rate limited", attempt=attempt, wait_s=wait)
logger.error("Query failed", cypher=cypher[:100], error=str(e))
```

**Rules:**
- One `logger = get_logger(__name__)` per file
- Use keyword arguments for structured context -- not f-string interpolation in messages
- Never log secrets (API keys, passwords, tokens)
- Log at entry and error points of significant operations

---

## Authentication

Auth lives in `graphrag_service/core/auth.py` using `X-API-Key` header validation:

```python
# graphrag_service/core/auth.py
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from .config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API key from request header."""
    if not api_key_header:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="No API key provided"
        )
    if api_key_header != get_settings().APP_X_API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API key")
    return api_key_header
```

**Usage in handlers:**

```python
from fastapi import APIRouter, Depends

from graphrag_service.core.auth import get_api_key

router = APIRouter()

@router.get("/protected")
async def protected_endpoint(api_key: str = Depends(get_api_key)):
    ...
```

---

## Database / Neo4j Patterns

### neomodel OGM

The project uses **neomodel** as the Neo4j OGM layer. The `Neo4jClient` in `graphrag_service/dbase/neo4j/client.py` wraps neomodel's `db.cypher_query()`:

```python
# graphrag_service/dbase/neo4j/client.py
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

    def run_query(self, cypher: str, params: dict | None = None) -> list:
        """Execute a raw Cypher query via neomodel's db.cypher_query."""
        results, meta = db.cypher_query(cypher, params or {})
        if not meta:
            return results
        return [dict(zip(meta, row)) for row in results]
```

### Parameterized Cypher -- always

```python
# Good -- Parameterized, safe
client.run_query(
    "MATCH (n:Paper {id: $id}) RETURN n",
    {"id": paper_id}
)

# Bad -- String interpolation, never
client.run_query(f"MATCH (n:Paper {{id: '{paper_id}'}}) RETURN n")
```

### MERGE over CREATE

```cypher
-- Good -- Idempotent, safe to re-run
MERGE (p:Paper {id: $id})
SET p.title = $title

-- Bad -- Duplicates on re-run
CREATE (p:Paper {id: $id, title: $title})
```

### Batch writes with UNWIND

```python
# Good -- One query for many nodes
cypher = "UNWIND $papers AS p MERGE (n:Paper {id: p.id}) SET n += p"
client.run_query(cypher, {"papers": papers_list})

# Bad -- One query per record
for paper in papers_list:
    client.run_query("MERGE (n:Paper {id: $id}) SET n.title = $title", paper)
```

---

## Testing Conventions

See [[projects/graphrag-neo4j/specs/conventions/testing]] for full test structure, naming, and BDD patterns.

Quick reference:
```
tests/
├── units/              # pytest, mocked Neo4j + OpenAI
├── integrations/       # pytest, real Neo4j (test instance)
└── e2e/
    └── {feature}/
        ├── mock/       # Full API tests with mocked services
        └── bdd/        # pytest-bdd, Gherkin, real services
```

Minimum coverage: **80%** (measured by `pytest --cov`).

---

## Related Conventions

- [[projects/graphrag-neo4j/specs/conventions/python-module-structure]] -- Module layering (Handler -> UseCase -> Service -> Repo)
- [[projects/graphrag-neo4j/specs/conventions/testing]] -- Test structure, BDD patterns
- [[projects/graphrag-neo4j/specs/conventions/security]] -- X-API-Key authentication

## External References

- [PEP 8](https://pep8.org/) -- Python style guide
- [Black](https://black.readthedocs.io/) -- Code formatter
- [isort](https://pycqa.github.io/isort/) -- Import sorter
- [Pydantic v2](https://docs.pydantic.dev/) -- Data validation
- [FastAPI](https://fastapi.tiangolo.com/) -- Web framework
- [neomodel](https://neomodel.readthedocs.io/) -- Neo4j OGM
- [structlog](https://www.structlog.org/) -- Structured logging
