---
created: 2026-03-02
source: https://raw.githubusercontent.com/nunenuh/sdd-python-service/refs/heads/main/specs/conventions/03-module-structure.md
---

# Python Module Structure Conventions

> **Project Mapping**: In `graphrag-neo4j`, all Python source lives in `backend/src/`.
> Feature modules live in `backend/src/modules/{name}/` following the Handler → UseCase → Service → Repository pattern.
> `library/rag/` and `library/graph/` are reusable internal packages that modules can import. The main router lives at `src/router.py` alongside `src/main.py`.

---

## How These Conventions Apply to graphrag-neo4j

| General Pattern | This Project Equivalent |
|-----------------|------------------------|
| `handler.py` (HTTP) | `src/router.py` or `src/modules/{name}/apiv1/handler.py` |
| `usecase.py` (Orchestration) | `src/library/rag/retriever.py`, `src/library/rag/generator.py`, or `src/modules/{name}/usecase.py` |
| `services.py` (Business Logic) | `src/library/rag/embedder.py`, `src/library/graph/parser.py`, or `src/modules/{name}/services.py` |
| `repositories.py` (Data Access) | `src/dbase/neo4j/client.py` or `src/modules/{name}/repositories.py` |
| `schemas.py` (Validation) | Pydantic models in `src/modules/{name}/schemas.py` |

**Backend `src/` structure:**
```
backend/src/                 # Python path root — imports start from here
├── main.py                  # App factory, CORS, router registration
├── router.py                # Main API router — endpoint definitions + Pydantic models
├── core/
│   ├── __init__.py
│   ├── config.py            # Pydantic Settings from env vars
│   └── security.py          # X-API-Key dependency
├── dbase/                   # Database layer
│   ├── __init__.py
│   └── neo4j/
│       ├── __init__.py
│       └── client.py        # Neo4j driver wrapper
├── library/                 # Reusable internal libraries
│   ├── __init__.py
│   ├── graph/               # Data domain (schema, parsing, ingestion)
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── parser.py
│   │   └── ingest.py
│   └── rag/                 # RAG domain (embed, retrieve, generate)
│       ├── __init__.py
│       ├── embedder.py
│       ├── retriever.py
│       └── generator.py
└── modules/                 # Feature modules (Handler → UseCase → Service → Repo)
    └── {module_name}/       # Example: papers/, methods/, tasks/, datasets/
        ├── __init__.py
        ├── apiv1/
        │   ├── __init__.py
        │   └── handler.py
        ├── schemas.py
        ├── usecase.py
        ├── services.py      # Add only when business logic needed
        └── repositories.py  # Add only when direct DB access needed
```

**Imports always resolve from `src/` (configured via `pythonpath = ["src"]` in `pyproject.toml`):**
```python
from core.config import settings           # src/core/config.py
from library.rag.embedder import batch_embed       # src/library/rag/embedder.py
from modules.papers.usecase import PapersUseCase  # src/modules/papers/usecase.py
```

---

## Example Module: `src/modules/papers/`

A `papers` module for querying ML papers from Neo4j — illustrates the full pattern.

### File structure

```
src/modules/papers/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py
├── schemas.py
├── usecase.py
├── services.py
└── repositories.py
```

### `__init__.py`

```python
"""
Papers module — query and explore ML research papers from Neo4j.
"""
```

### `schemas.py`

```python
"""
Papers schemas — Pydantic request/response models.
"""
from pydantic import BaseModel, Field


class PaperResponse(BaseModel):
    id: str
    title: str
    abstract: str
    url: str
    year: int | None = None


class PaperListResponse(BaseModel):
    items: list[PaperResponse]
    total: int


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search term")
    limit: int = Field(default=10, ge=1, le=100)
```

### `repositories.py`

```python
"""
Papers repository — Neo4j data access for Paper nodes.
"""
from dbase.neo4j.client import Neo4jClient


class PapersRepository:
    """Data access for :Paper nodes in Neo4j."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def find_by_id(self, paper_id: str) -> dict | None:
        """Return a single Paper node by ID, or None if not found."""
        results = self.client.run_query(
            "MATCH (p:Paper {id: $id}) RETURN p",
            {"id": paper_id},
        )
        return results[0]["p"] if results else None

    def find_all(self, limit: int = 10) -> list[dict]:
        """Return up to `limit` Paper nodes."""
        return self.client.run_query(
            "MATCH (p:Paper) RETURN p LIMIT $limit",
            {"limit": limit},
        )

    def search_by_title(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search on paper titles (case-insensitive contains)."""
        return self.client.run_query(
            """
            MATCH (p:Paper)
            WHERE toLower(p.title) CONTAINS toLower($query)
            RETURN p
            LIMIT $limit
            """,
            {"query": query, "limit": limit},
        )

    def count(self) -> int:
        """Return total number of Paper nodes."""
        result = self.client.run_query("MATCH (p:Paper) RETURN count(p) AS total")
        return result[0]["total"] if result else 0
```

### `services.py`

```python
"""
Papers services — business logic for paper operations.
"""
from dbase.neo4j.client import Neo4jClient
from modules.papers.repositories import PapersRepository
from modules.papers.schemas import PaperResponse


class PapersService:
    """Business logic for ML papers."""

    def __init__(self, client: Neo4jClient) -> None:
        self.repository = PapersRepository(client)

    def search(self, query: str, limit: int = 10) -> list[PaperResponse]:
        """Search papers by title and return as response models."""
        raw_papers = self.repository.search_by_title(query, limit)
        return [self._to_response(p["p"]) for p in raw_papers]

    def get_by_id(self, paper_id: str) -> PaperResponse | None:
        """Return a single paper or None."""
        raw = self.repository.find_by_id(paper_id)
        return self._to_response(raw) if raw else None

    def _to_response(self, node: dict) -> PaperResponse:
        """Map a Neo4j node dict to PaperResponse (immutable)."""
        return PaperResponse(
            id=node.get("id", ""),
            title=node.get("title", ""),
            abstract=node.get("abstract", ""),
            url=node.get("url", ""),
            year=node.get("year"),
        )
```

### `usecase.py`

```python
"""
Papers use case — orchestration layer for paper operations.
"""
from core.config import settings
from dbase.neo4j.client import Neo4jClient
from modules.papers.schemas import PaperListResponse, PaperResponse, PaperSearchRequest
from modules.papers.services import PapersService


class PapersUseCase:
    """Orchestrates paper queries. Always required — even for simple modules."""

    def __init__(self) -> None:
        self._client = Neo4jClient(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        self._service = PapersService(self._client)

    def search_papers(self, request: PaperSearchRequest) -> PaperListResponse:
        """Search papers by title query."""
        items = self._service.search(request.query, request.limit)
        return PaperListResponse(items=items, total=len(items))

    def get_paper(self, paper_id: str) -> PaperResponse | None:
        """Get a single paper by ID."""
        return self._service.get_by_id(paper_id)
```

### `apiv1/handler.py`

```python
"""
Papers API v1 — HTTP endpoints for ML paper queries.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from core.security import verify_api_key
from modules.papers.schemas import PaperListResponse, PaperResponse, PaperSearchRequest
from modules.papers.usecase import PapersUseCase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])


@router.post(
    "/search",
    response_model=PaperListResponse,
    dependencies=[Depends(verify_api_key)],
)
async def search_papers(request: PaperSearchRequest) -> PaperListResponse:
    """Search ML papers by title keyword."""
    try:
        usecase = PapersUseCase()
        return usecase.search_papers(request)
    except Exception as e:
        logger.error(f"Paper search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Paper search failed",
        )


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_paper(paper_id: str) -> PaperResponse:
    """Get a single paper by ID."""
    usecase = PapersUseCase()
    paper = usecase.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper
```

### Register in `src/main.py`

```python
from modules.papers.apiv1.handler import router as papers_router

app.include_router(papers_router, prefix="/api/v1")
# → POST /api/v1/papers/search
# → GET  /api/v1/papers/{paper_id}
```

---

## Original Convention (General FastAPI Service Pattern)

The following is the general Python module structure convention from the `sdd-python-service` template. Apply its **principles** to this project, mapping to the structure above.

---

# Module Structure Conventions

Complete guide for organizing feature modules within `src/fastapi_service/modules/`.

**Source**: Actual codebase patterns and architectural decisions

## Overview

Modules are groups of related features. Each module follows a consistent layered architecture pattern:

```
Handler (HTTP) → UseCase (Orchestration) → Service (Business Logic) → Repository (Data Access) → Database
```

## Module Naming

- **Use singular nouns**: `article`, `crawler`, `source`, `health`
- **Maximum 2 words**: `crawl_log`, `user_profile` (if needed)
- **Lowercase with underscores**: `news_source`, not `NewsSource` or `news-source`
- **Descriptive**: Name should clearly indicate the module's purpose

**Examples**:
- ✅ `articles` - Managing news articles
- ✅ `crawler` - Web crawling functionality
- ✅ `sources` - News source management
- ✅ `health` - Health monitoring
- ❌ `article` - Use plural for collections
- ❌ `crawler_module` - Redundant suffix
- ❌ `NewsSource` - Wrong case

## Required Components

Every module **MUST** have these components:

### 1. `__init__.py`

Module initialization file with module docstring.

**Example**:
```python
"""
Articles module for managing news articles.
"""
```

**Location**: `src/fastapi_service/modules/{module_name}/__init__.py`

### 2. `apiv1/handler.py`

HTTP request/response handlers (FastAPI routes).

**Responsibilities**:
- Define API endpoints
- Handle HTTP request/response
- Validate input via Pydantic schemas
- Call use cases
- Handle HTTP exceptions
- Return appropriate HTTP status codes

**Structure**:
```python
"""
{Module} API endpoints.

This module provides HTTP endpoints for {module} management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.logging import get_logger
from ...dbase.sql.core.session import get_db_session
from ...shared.exceptions import ServiceException, ValidationException
from ..schemas import {Module}Create, {Module}Response, {Module}Update
from ..usecase import {Module}UseCase

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model={Module}Response, status_code=status.HTTP_201_CREATED)
async def create_{module}(
    {module}_data: {Module}Create,
    db: Session = Depends(get_db_session),
):
    """Create a new {module}."""
    try:
        usecase = {Module}UseCase(db=db)
        result = usecase.create_{module}({module}_data, db=db)
        return result
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ServiceException as e:
        logger.error(f"Failed to create {module}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
```

**Location**: `src/fastapi_service/modules/{module_name}/apiv1/handler.py`

**Note**: Also create `apiv1/__init__.py`:
```python
"""{Module} API v1 handlers."""
```

### 3. `schemas.py`

Pydantic models for request/response validation and serialization.

**Responsibilities**:
- Define request schemas (Create, Update)
- Define response schemas (Response, ListResponse)
- Define base schemas with common fields
- Validate data types and constraints

**Structure**:
```python
"""
{Module} schemas for request/response models.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class {Module}Base(BaseModel):
    """Base {module} schema with common fields."""

    field1: str = Field(..., description="Field description", max_length=100)
    field2: Optional[int] = Field(None, description="Optional field")


class {Module}Create({Module}Base):
    """Schema for creating a new {module}."""

    pass


class {Module}Update(BaseModel):
    """Schema for updating an existing {module}."""

    field1: Optional[str] = Field(None, description="Field description")
    field2: Optional[int] = Field(None, description="Optional field")


class {Module}Response({Module}Base):
    """Schema for {module} response."""

    id: int = Field(..., description="{Module} ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class {Module}ListResponse(BaseModel):
    """Schema for {module} list response."""

    items: List[{Module}Response] = Field(..., description="List of {modules}")
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Pagination limit")
```

**Location**: `src/fastapi_service/modules/{module_name}/schemas.py`

### 4. `usecase.py`

Use case orchestration layer.

**Responsibilities**:
- Orchestrate business logic workflows
- Coordinate between multiple services
- Handle transaction management
- Provide high-level operations
- Bridge between handlers and services

**Structure**:
```python
"""
{Module} use case orchestration layer.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ...dbase.sql.core.session import get_db_session
from ...shared.exceptions import ServiceException
from .schemas import {Module}Create, {Module}Update
from .services import {Module}Service


class {Module}UseCase:
    """Use case for orchestrating {module} operations."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize {module} use case."""
        self.db = db

    def _get_service(self, db: Session) -> {Module}Service:
        """Get {module} service instance."""
        return {Module}Service(db)

    def create_{module}(
        self, {module}_data: {Module}Create, db: Optional[Session] = None
    ) -> dict:
        """Create a new {module}."""
        db_session = db or next(get_db_session())
        try:
            service = self._get_service(db_session)
            return service.create_{module}({module}_data)
        except Exception as e:
            raise ServiceException(f"Failed to create {module}: {str(e)}")
```

**Location**: `src/fastapi_service/modules/{module_name}/usecase.py`

## Conditional Components

Add these components only when needed:

### 5. `repositories.py` (Conditional)

Data access layer for SQLAlchemy models.

**When to create**:
- ✅ Module needs to access database
- ✅ Module uses SQLAlchemy models
- ❌ Module has no database operations

**Structure**:
```python
"""
{Module} repository for data access operations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from ...dbase.sql.models.{module} import {Module}Model
from ...shared.exceptions import RepositoryException


class {Module}Repository:
    """Repository for {module} data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, {module}_data: dict) -> {Module}Model:
        """Create a new {module}."""
        try:
            {module} = {Module}Model(**{module}_data)
            self.db.add({module})
            self.db.commit()
            self.db.refresh({module})
            return {module}
        except Exception as e:
            self.db.rollback()
            raise RepositoryException(f"Failed to create {module}: {str(e)}")

    def get_by_id(self, {module}_id: int) -> Optional[{Module}Model]:
        """Get {module} by ID."""
        return self.db.query({Module}Model).filter({Module}Model.id == {module}_id).first()
```

### 6. `services.py` (Conditional)

Business logic layer.

**When to create**:
- ✅ Module has business logic beyond simple CRUD
- ✅ Module needs validation or transformation logic
- ❌ Module is purely CRUD (use repository directly in use case)

**Structure**:
```python
"""
{Module} business logic services.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from ...shared.exceptions import ServiceException, ValidationException
from .repositories import {Module}Repository
from .schemas import {Module}Create


class {Module}Service:
    """Service for {module} business logic."""

    def __init__(self, db: Session):
        self.repository = {Module}Repository(db)

    def create_{module}(self, {module}_data: {Module}Create) -> dict:
        """Create a new {module} with business validation."""
        existing = self.repository.get_by_field({module}_data.field)
        if existing:
            raise ValidationException(f"{Module} with field already exists")
        try:
            {module} = self.repository.create({module}_data.model_dump())
            return {"id": {module}.id, "field1": {module}.field1}
        except Exception as e:
            raise ServiceException(f"Failed to create {module}: {str(e)}")
```

### 7. `tasks.py` (Conditional)

Celery tasks for asynchronous/background processing.

**When to create**:
- ✅ Module needs Celery tasks or background jobs
- ❌ Module has no background processing needs

**Structure**:
```python
"""
Celery tasks for {module} module.
"""

from ...core.logging import get_logger
from ...dbase.sql.core.session import SessionLocal
from ...worker import app
from .usecase import {Module}UseCase

logger = get_logger(__name__)


@app.task(name="fastapi_service.modules.{module}.tasks.{task_name}", bind=True)
def {task_name}(self, param1: str, param2: int = None):
    """Celery task for {task description}."""
    db_session = SessionLocal()
    try:
        usecase = {Module}UseCase(db=db_session)
        result = usecase.{operation}(param1, param2)
        return result
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise
    finally:
        db_session.close()
```

## Module Structure Examples

### Simple Module (No Database)

```
health/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py
├── schemas.py
├── services.py      # No repository needed
└── usecase.py       # Still required for consistency
```

### Standard Module (With Database)

```
articles/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py
├── schemas.py
├── repositories.py  # Database access
├── services.py      # Business logic
└── usecase.py       # Orchestration
```

### Complex Module (With Tasks)

```
crawler/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py
├── schemas.py
├── repositories.py
├── services.py
├── usecase.py
├── tasks.py         # Celery tasks
└── scrapy/          # Special subdirectory
    └── spiders/
```

## Import Patterns

### Within Module

```python
# handler.py
from ..schemas import ArticleCreate, ArticleResponse
from ..usecase import ArticleUseCase

# usecase.py
from .services import ArticleService
from .schemas import ArticleCreate

# services.py
from .repositories import ArticleRepository
```

### From External Modules

```python
# Use absolute imports from package root
from ...dbase.sql.core.session import get_db_session
from ...shared.exceptions import ServiceException
from ...core.logging import get_logger
```

## File Organization Checklist

When creating a new module, ensure:

- [ ] Module name follows naming conventions (lowercase, max 2 words)
- [ ] `__init__.py` exists with module docstring
- [ ] `apiv1/handler.py` exists with API endpoints
- [ ] `apiv1/__init__.py` exists
- [ ] `schemas.py` exists with Pydantic models
- [ ] `usecase.py` exists (always required)
- [ ] `repositories.py` added only if database access needed
- [ ] `services.py` added only if business logic needed
- [ ] `tasks.py` added only if background jobs needed
- [ ] All imports use relative imports within module
- [ ] All imports use absolute imports for external modules

## Best Practices

1. **Keep handlers thin**: Handlers handle HTTP only, delegate to use cases
2. **Use cases orchestrate**: Coordinate between services and repositories
3. **Services contain business logic**: Business rules and validation go in services
4. **Repositories handle data access**: Database operations only in repositories
5. **Schemas validate**: Use Pydantic schemas for all input/output
6. **Consistent error handling**: Use shared exceptions
7. **Type hints everywhere**: All functions must have type hints
8. **Documentation**: All public functions must have docstrings
