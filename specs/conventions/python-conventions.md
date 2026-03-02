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
- Use **isort** for import sorting (profile: black)
- Use **ruff** for linting (replaces flake8)
- Use **mypy** for type checking

Configure in `pyproject.toml`:

```toml
[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]
```

### Type Hints

- **Required** on all function signatures — no exceptions
- Prefer built-in generic types (Python 3.11+): `list[str]`, `dict[str, float]`
- Use `Optional[T]` only for Python 3.9 compatibility; prefer `T | None` in 3.11+
- Avoid `Any` — define proper types

```python
# ✅ Python 3.11 style
def embed_texts(texts: list[str]) -> list[list[float]]: ...
def get_node(node_id: str) -> dict | None: ...

# ✅ Optional for nullable params
def search(query: str, limit: int = 5) -> list[dict]: ...

# ❌ No Any
def process(data: Any) -> Any: ...
```

### Async / Await

- FastAPI route handlers must be `async def`
- I/O operations (OpenAI, Neo4j) should use async when the client supports it
- `dbase/neo4j/client.py` uses the sync driver for simplicity — wrap with `asyncio.to_thread()` if needed

```python
# ✅ Route handler — always async
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    result = await asyncio.to_thread(retrieve, request.question, client)
    ...

# ✅ Pure function — sync is fine
def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
```

---

## Naming Conventions

### Files & Packages

| Thing | Convention | Example |
|-------|-----------|---------|
| Modules | `snake_case.py` | `client.py`, `embedder.py` |
| Packages | `snake_case/` | `library/rag/`, `library/graph/`, `core/` |
| Test files | `test_*.py` | `test_embedder.py` |

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
import logging
import re
from pathlib import Path
from typing import Iterator

# 2. Third-party
import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 3. Local (relative)
from core.config import settings
from dbase.neo4j.client import Neo4jClient
from library.rag.embedder import embed_text
```

**Rules:**
- Use **absolute imports** within the `backend/` package
- Relative imports (`from .embedder import ...`) only within the same subpackage
- Sort with `isort --profile black`
- No star imports (`from module import *`)

---

## Function Design

### Size limit: 50 lines per function

If a function grows past 50 lines, extract a helper.

### Single responsibility

One function, one purpose:

```python
# ✅ Single responsibility
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

# ❌ Mixed concerns
def process_and_save_paper(raw: dict, client: Neo4jClient) -> None:
    title = raw["title"].strip()
    # ... clean, embed, save — all in one function
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
# ✅ Immutable — returns new dict
def attach_embedding(entity: dict, embedding: list[float]) -> dict:
    return {**entity, "embedding": embedding}

# ✅ Immutable list comprehension
def attach_embeddings(entities: list[dict], embeddings: list[list[float]]) -> list[dict]:
    return [{**e, "embedding": emb} for e, emb in zip(entities, embeddings)]

# ❌ Mutates input
def attach_embedding(entity: dict, embedding: list[float]) -> dict:
    entity["embedding"] = embedding  # ❌ side effect
    return entity
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
- `Field(default_factory=dict)` for optional dict/list — never `= {}` or `= []`
- `from_attributes = True` in `Config` only when converting from ORM objects
- One schema file per module if schemas are complex; inline in `routes.py` if simple

---

## Error Handling

### Always explicit, never silent

```python
# ✅ Explicit — typed exceptions, meaningful messages
try:
    result = client.run_query(cypher, params)
except ServiceUnavailableError as e:
    logger.error("Neo4j unavailable", extra={"error": str(e)})
    raise HTTPException(status_code=503, detail="Database unavailable")
except Exception as e:
    logger.error("Unexpected query error", extra={"error": str(e), "cypher": cypher})
    raise

# ❌ Silent swallow — never do this
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
# shared/exceptions.py
class GraphRAGException(Exception):
    """Base exception for graphrag-neo4j."""

class EmbeddingError(GraphRAGException):
    """OpenAI embedding failed."""

class RetrievalError(GraphRAGException):
    """Neo4j vector search or traversal failed."""

class GenerationError(GraphRAGException):
    """LLM answer generation failed."""

class IngestionError(GraphRAGException):
    """Data ingestion pipeline failed."""
```

---

## Logging

Use Python's `logging` module. Configure via `LOG_LEVEL` env var.

```python
import logging
logger = logging.getLogger(__name__)  # Module-level logger

# Structured context via extra dict
logger.info("Batch embedded", extra={"batch": i, "total": total_batches, "size": len(batch)})
logger.warning("Rate limited", extra={"attempt": attempt, "wait_s": wait})
logger.error("Query failed", extra={"cypher": cypher[:100], "error": str(e)})
```

**Rules:**
- One `logger = logging.getLogger(__name__)` per file
- Use `extra={}` dict for structured context — not f-string interpolation in messages
- Never log secrets (API keys, passwords, tokens)
- Log at entry and error points of significant operations

---

## Database / Neo4j Patterns

### Parameterized Cypher — always

```python
# ✅ Parameterized — safe
client.run_query(
    "MATCH (n:Paper {id: $id}) RETURN n",
    {"id": paper_id}
)

# ❌ String interpolation — never
client.run_query(f"MATCH (n:Paper {{id: '{paper_id}'}}) RETURN n")
```

### MERGE over CREATE

```cypher
-- ✅ Idempotent — safe to re-run
MERGE (p:Paper {id: $id})
SET p.title = $title

-- ❌ Duplicates on re-run
CREATE (p:Paper {id: $id, title: $title})
```

### Batch writes with UNWIND

```python
# ✅ One query for many nodes
cypher = "UNWIND $papers AS p MERGE (n:Paper {id: p.id}) SET n += p"
client.run_query(cypher, {"papers": papers_list})

# ❌ One query per record
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

- [[projects/graphrag-neo4j/specs/conventions/python-module-structure]] — Module layering (Handler → UseCase → Service → Repo)
- [[projects/graphrag-neo4j/specs/conventions/testing]] — Test structure, BDD patterns
- [[projects/graphrag-neo4j/specs/conventions/security]] — X-API-Key authentication

## External References

- [PEP 8](https://pep8.org/) — Python style guide
- [Black](https://black.readthedocs.io/) — Code formatter
- [isort](https://pycqa.github.io/isort/) — Import sorter
- [Pydantic v2](https://docs.pydantic.dev/) — Data validation
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
