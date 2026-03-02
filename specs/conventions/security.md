# Security Conventions — FastAPI with X-API-Key

Security guidelines for `graphrag-neo4j` backend using API key authentication.

---

## Overview

The API uses **X-API-Key header authentication** — a simple, stateless mechanism suitable for portfolio demos and internal services. Every protected endpoint verifies the key before processing the request.

```
Client → Request with X-API-Key header
                ↓
         verify_api_key dependency
                ↓
     ✅ Valid key → proceed to handler
     ❌ Invalid/missing key → 401 Unauthorized
```

---

## Environment Variable Setup

The API key **must never be hardcoded**. Store it in `.env`:

```bash
# .env
API_KEY=your-secret-key-here   # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY_ENABLED=true           # Set to false to disable auth (local dev without key)
```

Add to `core/config.py`:

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    openai_api_key: str
    api_key: str = ""                  # Empty = auth disabled
    api_key_enabled: bool = True       # True by default (secure by default)
    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"

settings = Settings()
```

**Generating a secure key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: gTZ8kR5mJ2nPqWvXhLdYeAsOuCfBiNwE7t1r4y6p9q0
```

---

## The Security Dependency

Create `core/security.py`:

```python
"""
core/security.py

FastAPI dependency for X-API-Key authentication.
Attach to routes or routers that require authentication.
"""
import logging
import secrets

from fastapi import Header, HTTPException, status
from fastapi.security import APIKeyHeader

from core.config import settings

logger = logging.getLogger(__name__)

# OpenAPI UI shows this as the auth field name
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    FastAPI dependency: verify the X-API-Key header.

    Skips verification if:
    - api_key_enabled is False (disabled in config)
    - api_key is empty (not configured)

    Raises:
        HTTPException 401: If key is missing or invalid.

    Usage:
        @router.post("/query", dependencies=[Depends(verify_api_key)])
        @router.get("/graph/explore", dependencies=[Depends(verify_api_key)])
    """
    # Bypass if auth is disabled or key not configured
    if not settings.api_key_enabled or not settings.api_key:
        return

    # Missing key
    if not x_api_key:
        logger.warning("Request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Compare using secrets.compare_digest — prevents timing attacks
    provided = x_api_key.encode("utf-8")
    expected = settings.api_key.encode("utf-8")

    if not secrets.compare_digest(provided, expected):
        logger.warning("Invalid X-API-Key attempt", extra={"key_prefix": x_api_key[:4]})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
```

---

## Applying to Routes

### Option A: Per-router (recommended — protects all routes at once)

```python
# router.py
from fastapi import APIRouter, Depends
from core.security import verify_api_key

# All routes in this router require authentication
router = APIRouter(dependencies=[Depends(verify_api_key)])

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    ...  # verify_api_key already called before this runs

@router.get("/graph/explore", response_model=ExploreResponse)
async def graph_explore(limit: int = Query(default=50)) -> ExploreResponse:
    ...
```

### Option B: Per-endpoint (fine-grained control)

```python
@router.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
async def query(request: QueryRequest) -> QueryResponse:
    ...

# Public endpoint — no auth
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    ...
```

### Option C: Exempt specific routes from a protected router

```python
# main.py — mount a public router separately
from api import routes_public, routes_protected

app.include_router(routes_public.router, prefix="/api")           # No auth
app.include_router(
    routes_protected.router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
)
```

**Recommendation for graphrag-neo4j:**
- `/api/health` → **public** (monitoring tools need this without auth)
- `/api/query` → **protected**
- `/api/graph/explore` → **protected**
- `/api/graph/schema` → **protected**

---

## `main.py` with Split Routers

```python
# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from router import router as protected_router
from modules.health.apiv1.handler import router as health_router
from core.config import settings
from core.security import verify_api_key

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
    dependencies=[Depends(verify_api_key)],
)
```

---

## Frontend: Sending the API Key

```typescript
// frontend/src/lib/api.ts
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
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
| Never hardcode keys | Always use `.env` → `settings.api_key` |
| Never log the full key | Log only first 4 chars for debugging: `key[:4]` |
| Use `secrets.compare_digest` | Prevents timing attacks on string comparison |
| Rotate on exposure | If key is committed to git, rotate immediately |
| Use `token_urlsafe(32)` | 256-bit entropy — sufficient for API key |

### Timing Attack Prevention

```python
# ✅ Constant-time comparison — not vulnerable to timing attacks
if not secrets.compare_digest(provided, expected):
    raise HTTPException(...)

# ❌ Short-circuit comparison — timing side channel
if provided != expected:
    raise HTTPException(...)
```

### Error Response Rules

| Scenario | Status | Response Body |
|----------|--------|--------------|
| Missing `X-API-Key` | 401 | `{"detail": "Missing API key. Provide X-API-Key header."}` |
| Wrong key value | 401 | `{"detail": "Invalid API key."}` |
| Key disabled (`api_key_enabled=false`) | — | Request passes through |

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
    allow_headers=["*"],   # ← Must include X-API-Key (wildcard covers it)
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
    monkeypatch.setattr("core.security.settings.api_key", TEST_API_KEY)
    monkeypatch.setattr("core.security.settings.api_key_enabled", True)

@pytest.fixture
def auth_headers() -> dict:
    """HTTP headers with valid API key for test requests."""
    return {"X-API-Key": TEST_API_KEY}

@pytest.fixture
def no_auth_headers() -> dict:
    """HTTP headers without API key (for testing 401)."""
    return {}
```

```python
# tests/e2e/query/mock/test_query_mock.py
def test_query_with_valid_key_returns_200(auth_headers):
    response = client.post("/api/query", json={"question": "test"}, headers=auth_headers)
    assert response.status_code == 200

def test_query_without_key_returns_401():
    response = client.post("/api/query", json={"question": "test"})
    assert response.status_code == 401
    assert "Missing API key" in response.json()["detail"]

def test_query_with_wrong_key_returns_401():
    response = client.post("/api/query", json={"question": "test"}, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401

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
    Then the response status is 401
    And the response detail contains "Missing API key"

  Scenario: Valid API key grants access
    Given the API is running
    And I have a valid API key
    When I send a POST to "/api/query" with the API key
    Then the response status is not 401
```

---

## OpenAPI Documentation

FastAPI auto-documents the security scheme when you use `APIKeyHeader`:

```python
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
```

The Swagger UI at `/docs` will show a lock icon and "Authorize" button where users can enter their API key for testing. This is automatically wired by FastAPI — no extra config needed.

---

## Docker Compose Secret Injection

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    env_file: .env         # API_KEY loaded from here
    environment:
      - API_KEY_ENABLED=true
```

**Never commit `.env`** with real keys. Only commit `.env.example`:

```bash
# .env.example — commit this
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=CHANGE_ME
OPENAI_API_KEY=sk-CHANGE_ME
API_KEY=CHANGE_ME
API_KEY_ENABLED=true
ALLOWED_ORIGINS=http://localhost:5173
```

Add `.env` to `.gitignore`:
```bash
echo ".env" >> .gitignore
```
