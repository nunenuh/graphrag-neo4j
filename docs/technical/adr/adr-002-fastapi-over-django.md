# ADR-002: Use FastAPI over Django/Flask for the Backend

**Date:** 2026-03-02
**Status:** Accepted

---

## Context

The backend needs to serve 4 API endpoints, connect to Neo4j, call OpenAI, and handle async I/O. We need to choose a Python web framework.

---

## Decision

Use **FastAPI** with `uvicorn`.

---

## Alternatives Considered

### Django REST Framework
- Full-featured, batteries-included
- Heavy for 4 endpoints
- Sync by default (async support exists but non-idiomatic)
- ORM designed for SQL — no benefit here (we use Neo4j)

### Flask
- Lightweight and familiar
- No native async support (Flask 2.x has limited async)
- No built-in request validation or OpenAPI generation
- Requires more boilerplate

### FastAPI (chosen)
- Native async/await — matches OpenAI and Neo4j I/O patterns
- Pydantic models for automatic request validation and response serialization
- Auto-generated OpenAPI docs at `/docs`
- Type hints throughout — readable and self-documenting
- Fast to set up — < 50 lines for the full API skeleton

---

## Consequences

- Automatic `/docs` and `/redoc` endpoints for free (useful for portfolio)
- Pydantic models serve as living API documentation
- Async handlers ready for streaming responses in v2
