# Security Conventions — FastAPI with X-API-Key

Security guidelines for `graphrag-neo4j` backend using API key authentication.

---

## Overview

The API uses **X-API-Key header authentication** — a simple, stateless mechanism suitable for portfolio demos and internal services. Every protected endpoint verifies the key before processing the request.

```
Client -> Request with X-API-Key header
                |
         get_api_key dependency
                |
     Valid key -> proceed to handler
     Invalid/missing key -> 403 Forbidden
```

---

## Environment Variable Setup

The API key **must never be hardcoded**. Store it in `.env`:

```bash
# .env
APP_X_API_KEY=your-secret-key-here   # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The settings class in `core/config.py`:

```python
# graphrag_service/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    openai_api_key: str
    APP_X_API_KEY: str = ""            # Empty = no key set (all requests pass)
    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()
```

**Generating a secure key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: gTZ8kR5mJ2nPqWvXhLdYeAsOuCfBiNwE7t1r4y6p9q0
```

---

## The Security Dependency

Create `core/auth.py`:

```python
"""
graphrag_service/core/auth.py

FastAPI dependency for X-API-Key authentication.
Attach to routes or routers that require authentication.
"""
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from .config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    FastAPI dependency: verify the X-API-Key header.

    Always validates when APP_X_API_KEY is set in settings.
    There is no toggle to disable auth — if the key is configured,
    it is enforced.

    Raises:
        HTTPException 403: If key is missing or invalid.

    Usage:
        @router.post("/query", dependencies=[Depends(get_api_key)])
        @router.get("/graph/explore", dependencies=[Depends(get_api_key)])
    """
    if not api_key_header:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="No API key provided",
        )
    if api_key_header != get_settings().APP_X_API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key_header
```

---

## Applying to Routes

### Option A: Per-router (recommended — protects all routes at once)

```python
# graphrag_service/router.py
from fastapi import APIRouter, Depends
from graphrag_service.core.auth import get_api_key

# All routes in this router require authentication
router = APIRouter(dependencies=[Depends(get_api_key)])

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    ...  # get_api_key already called before this runs

@router.get("/graph/explore", response_model=ExploreResponse)
async def graph_explore(limit: int = Query(default=50)) -> ExploreResponse:
    ...
```

### Option B: Per-endpoint (fine-grained control)

```python
@router.post("/query", response_model=QueryResponse, dependencies=[Depends(get_api_key)])
async def query(request: QueryRequest) -> QueryResponse:
    ...

# Public endpoint — no auth
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    ...
```

### Option C: Exempt specific routes from a protected router

```python
# graphrag_service/main.py — mount a public router separately
from graphrag_service.router import router as protected_router
from graphrag_service.modules.health.apiv1.handler import router as health_router

app.include_router(health_router, prefix="/api")           # No auth
app.include_router(
    protected_router,
    prefix="/api",
    dependencies=[Depends(get_api_key)],
)
```

**Recommendation for graphrag-neo4j:**
- `/api/health` -> **public** (monitoring tools need this without auth)
- `/api/query` -> **protected**
- `/api/graph/explore` -> **protected**
- `/api/graph/schema` -> **protected**

---

## `main.py` with Split Routers

```python
# graphrag_service/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from graphrag_service.router import router as protected_router
from graphrag_service.modules.health.apiv1.handler import router as health_router
from graphrag_service.core.config import get_settings
from graphrag_service.core.auth import get_api_key

settings = get_settings()

app = FastAPI(title="graphrag-neo4j", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes (no auth)
app.include_router(health_router, prefix="/api")

# Protected routes (X-API-Key required)
app.include_router(
    protected_router,
    prefix="/api",
    dependencies=[Depends(get_api_key)],
)
```

---

## Frontend: Sending the API Key

```typescript
// frontend/src/lib/api.ts
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8005";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";  // Set in frontend/.env

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Attach key only if configured
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  ...
}
```

```bash
# frontend/.env
VITE_API_KEY=your-secret-key-here
```

**Security note**: `VITE_API_KEY` is embedded in the frontend bundle at build time.
For a portfolio demo, this is acceptable. For production, use a backend-for-frontend pattern instead.

---

## Security Rules

### Key Management

| Rule | Detail |
|------|--------|
| Never hardcode keys | Always use `.env` -> `get_settings().APP_X_API_KEY` |
| Never log the full key | Log only first 4 chars for debugging: `key[:4]` |
| Rotate on exposure | If key is committed to git, rotate immediately |
| Use `token_urlsafe(32)` | 256-bit entropy — sufficient for API key |

### Error Response Rules

| Scenario | Status | Response Body |
|----------|--------|--------------|
| Missing `X-API-Key` | 403 | `{"detail": "No API key provided"}` |
| Wrong key value | 403 | `{"detail": "Invalid API key"}` |

**Never reveal in the error response:**
- Whether the key exists
- The key format or length
- Specific mismatch reason

---

## CORS + Auth Together

CORS and X-API-Key work at different layers:

| Layer | Enforced by | What it protects |
|-------|------------|-----------------|
| CORS | Browser only | Prevents unauthorized browser-based cross-origin calls |
| X-API-Key | Server | Protects all callers (browsers, curl, scripts) |

Configure CORS to allow the `X-API-Key` header:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],   # Must include X-API-Key (wildcard covers it)
)
```

If you restrict headers, be explicit:
```python
allow_headers=["Content-Type", "X-API-Key"],
```

---

## Testing with X-API-Key

### Unit / Mock E2E Tests

```python
# tests/conftest.py
import pytest

TEST_API_KEY = "test-key-for-unit-tests"

@pytest.fixture(autouse=True)
def set_test_api_key(monkeypatch):
    """Set test API key in settings for all tests."""
    monkeypatch.setenv("APP_X_API_KEY", TEST_API_KEY)

@pytest.fixture
def auth_headers() -> dict:
    """HTTP headers with valid API key for test requests."""
    return {"X-API-Key": TEST_API_KEY}

@pytest.fixture
def no_auth_headers() -> dict:
    """HTTP headers without API key (for testing 403)."""
    return {}
```

```python
# tests/e2e/query/mock/test_query_mock.py
def test_query_with_valid_key_returns_200(auth_headers):
    response = client.post("/api/query", json={"question": "test"}, headers=auth_headers)
    assert response.status_code == 200

def test_query_without_key_returns_403():
    response = client.post("/api/query", json={"question": "test"})
    assert response.status_code == 403
    assert "No API key provided" in response.json()["detail"]

def test_query_with_wrong_key_returns_403():
    response = client.post("/api/query", json={"question": "test"}, headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_health_is_public():
    """Health endpoint requires no auth."""
    response = client.get("/api/health")  # No headers
    assert response.status_code == 200
```

### BDD Test with Auth

```gherkin
# tests/e2e/health/bdd/features/health.feature (extend existing)

  Scenario: Protected endpoint requires API key
    Given the API is running
    When I send a POST to "/api/query" without an API key
    Then the response status is 403
    And the response detail contains "No API key provided"

  Scenario: Valid API key grants access
    Given the API is running
    And I have a valid API key
    When I send a POST to "/api/query" with the API key
    Then the response status is not 403
```

---

## OpenAPI Documentation

FastAPI auto-documents the security scheme when you use `APIKeyHeader`:

```python
from fastapi.security.api_key import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
```

The Swagger UI at `/docs` will show a lock icon and "Authorize" button where users can enter their API key for testing. This is automatically wired by FastAPI — no extra config needed.

---

## Docker Compose Secret Injection

```yaml
# docker/docker-compose.yml
services:
  backend:
    build: ../backend
    env_file: ../.env        # APP_X_API_KEY loaded from here
    ports:
      - "8005:8005"
```

**Never commit `.env`** with real keys. Only commit `env.example`:

```bash
# env.example — commit this
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=CHANGE_ME
OPENAI_API_KEY=sk-CHANGE_ME
APP_X_API_KEY=CHANGE_ME
ALLOWED_ORIGINS=http://localhost:5173
```

Add `.env` to `.gitignore`:
```bash
echo ".env" >> .gitignore
```
