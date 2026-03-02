---
created: 2026-03-02
source: https://raw.githubusercontent.com/nunenuh/sdd-python-service/refs/heads/main/specs/conventions/00-repository-overview.md
---

# Repository Overview

> **Project Mapping**: This document describes the general `fastapi-service` template structure.
> For how it maps to `graphrag-neo4j`, see the project-specific section below.

---

## graphrag-neo4j Repository Structure

Root is minimal — only infrastructure files. Each service (`backend/`, `frontend/`) is **fully independent** with its own dependency manager, Dockerfile, and `.env`.

```
graphrag-neo4j/                  # Root — GitHub repo root
├── docker-compose.yml           # Orchestrates all services
├── .env.example                 # Template for root-level secrets (Neo4j, OpenAI, API_KEY)
├── .gitignore
├── README.md
├── data/                        # Papers With Code data (shared by backend)
│   ├── download.sh              # Fetch PwC JSON dumps
│   ├── papers.json
│   ├── methods.json
│   ├── tasks.json
│   ├── datasets.json
│   └── evaluations.json
├── docs/                        # Design decisions, ADRs, product docs
│   ├── product/
│   └── technical/
└── specs/                       # Implementation guide
    ├── conventions/
    ├── backend/
    └── frontend/
```

### `backend/` — Independent Python Service

Has its own Poetry setup, Dockerfile, and tests. All Python source lives in `backend/src/`. No Python tooling at repo root.

```
backend/
├── pyproject.toml               # Poetry: deps + tool config (pythonpath = ["src"])
├── poetry.lock
├── Dockerfile                   # Multi-stage: build → runtime image
├── .env                         # Local dev (not committed — copy from root .env.example)
│
├── src/                         # ← ALL Python source lives here
│   ├── main.py                  # FastAPI app factory, CORS, router
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings (reads .env)
│   │   └── security.py          # X-API-Key dependency
│   ├── dbase/                   # Database layer
│   │   ├── __init__.py
│   │   └── neo4j/
│   │       ├── __init__.py
│   │       └── client.py        # Neo4j driver wrapper (run_query)
│   ├── library/                 # Reusable internal libraries
│   │   ├── __init__.py
│   │   ├── graph/               # Data layer (schema + ingestion)
│   │   │   ├── __init__.py
│   │   │   ├── schema.py        # CREATE CONSTRAINT / CREATE INDEX
│   │   │   ├── parser.py        # PwC JSON → clean entity dicts
│   │   │   └── ingest.py        # Orchestrate: parse → embed → load
│   │   └── rag/                 # RAG pipeline
│   │       ├── __init__.py
│   │       ├── embedder.py      # OpenAI embedding (single + batch)
│   │       ├── retriever.py     # Vector search → graph traversal
│   │       └── generator.py     # Context serialize + LLM call
│   ├── router.py                # Main API router — endpoint definitions + Pydantic models
│   └── modules/                 # Feature modules (Handler → UseCase → Service → Repo)
│       └── {module_name}/       # Example: papers/, methods/, tasks/
│           ├── __init__.py      # Module docstring
│           ├── apiv1/
│           │   ├── __init__.py
│           │   └── handler.py   # FastAPI routes for this module
│           ├── schemas.py       # Pydantic request/response models
│           ├── usecase.py       # Orchestration layer (always required)
│           ├── services.py      # Business logic (add when needed)
│           └── repositories.py  # Data access (add when needed)
│
└── tests/                       # All Python tests
    ├── conftest.py              # Shared fixtures
    ├── unit/                    # Unit tests — mirrors src/ structure
    │   ├── conftest.py
    │   ├── library/
    │   │   ├── rag/
    │   │   │   ├── test_embedder.py
    │   │   │   ├── test_retriever.py
    │   │   │   └── test_generator.py
    │   │   └── graph/
    │   │       └── test_parser.py
    │   ├── core/
    │   │   └── test_config.py
    │   └── dbase/
    │       └── neo4j/
    │           └── test_client.py
    ├── integration/             # Integration tests — mirrors src/ structure, real Neo4j
    │   ├── conftest.py          # Real Neo4j test client
    │   └── library/
    │       └── graph/
    │           ├── test_schema.py
    │           ├── test_ingest.py
    │           └── test_retriever_neo4j.py
    └── e2e/
        ├── query/
        │   ├── mock/test_query_mock.py
        │   └── bdd/
        │       ├── features/query.feature
        │       └── test_query_bdd.py
        ├── graph/
        │   ├── mock/test_graph_mock.py
        │   └── bdd/
        │       ├── features/graph.feature
        │       └── test_graph_bdd.py
        └── health/
            ├── mock/test_health_mock.py
            └── bdd/
                ├── features/health.feature
                └── test_health_bdd.py
```

**`src/` is the Python path root.** All imports are relative to `src/`:
```python
from core.config import settings       # ✅ src/core/config.py
from library.rag.embedder import embed_text  # ✅ src/library/rag/embedder.py
from modules.papers.usecase import PapersUseCase  # ✅ src/modules/papers/usecase.py
```

**Module structure convention** (`src/modules/{name}/`) follows the Handler → UseCase → Service → Repository pattern. See [[projects/graphrag-neo4j/specs/conventions/python-module-structure]] for full detail.

### `frontend/` — Independent React App

Has its own npm setup and Dockerfile. No Node tooling at root.

```
frontend/
├── package.json                 # npm: dependencies + scripts (dev, build, test, lint)
├── package-lock.json            # Locked dependency versions
├── Dockerfile                   # Multi-stage: build → nginx static image
├── .env                         # Local dev: VITE_API_URL, VITE_API_KEY (not committed)
├── .env.example                 # Template for frontend env vars
├── index.html
├── vite.config.ts               # Vite config + @ path alias
├── tsconfig.json                # Strict TypeScript config
├── tailwind.config.ts           # Tailwind + shadcn CSS variables
├── postcss.config.js
└── src/
    ├── App.tsx                  # Root layout, all query state
    ├── main.tsx                 # React DOM entry point
    ├── components/
    │   ├── ui/                  # shadcn/ui generated (owned, not versioned)
    │   ├── ChatPanel.tsx
    │   ├── GraphViewer.tsx
    │   └── CypherPanel.tsx
    ├── lib/
    │   └── api.ts               # Fetch wrapper, all API calls
    └── types/
        └── api.ts               # TypeScript interfaces mirroring API spec
```

---

## Tech Stack

| Layer                 | Technology                                       |
| --------------------- | ------------------------------------------------ |
| Runtime               | Python 3.11+                                     |
| Framework             | FastAPI + Uvicorn                                |
| Graph + Vector DB     | Neo4j 5.15 Community                             |
| Frontend              | Vite + React + TypeScript + Tailwind + shadcn/ui |
| LLM                   | OpenAI GPT-4o-mini                               |
| Embeddings            | OpenAI text-embedding-3-small (1536 dims)        |
| Visualization         | react-force-graph-2d                             |
| Infra                 | Docker Compose                                   |
| Data                  | Papers With Code (5k paper subset)               |
| Dependency Management | Poetry (backend), npm (frontend)                 |

---

## Architecture Pattern

`graphrag-neo4j` follows a simplified layered architecture:

```
API Routes (router.py)
    ↓
Library (library/rag/, library/graph/)
    ↓
Neo4j Client (dbase/neo4j/client.py)
    ↓
Neo4j Database
```

Mapping to the general pattern from `sdd-python-service`:

| General Pattern | graphrag-neo4j Equivalent |
|----------------|--------------------------|
| `Handler` | `router.py` — FastAPI endpoints |
| `UseCase` | `library/rag/retriever.py`, `library/rag/generator.py` — orchestration |
| `Service` | `library/rag/embedder.py`, `library/graph/parser.py` — business logic |
| `Repository` | `dbase/neo4j/client.py` — data access |

---

## Key Patterns

1. **Layered Architecture**: `router.py` → RAG/Graph → Neo4j Client
2. **Dependency Injection**: `settings` singleton from `core/config.py`
3. **Graph Pattern**: All data access via parameterized Cypher — never string interpolation
4. **Immutability**: All transform functions return new dicts, never mutate inputs
5. **Batch Processing**: OpenAI embeddings in batches of 100, Neo4j writes via `UNWIND`

---

## Entry Points

| Entry Point | Run From | Command | Purpose |
|------------|----------|---------|---------|
| `backend/main.py` | `backend/` | `poetry run uvicorn main:app --reload` | FastAPI dev server |
| `backend/src/library/graph/schema.py` | `backend/` | `poetry run python src/library/graph/schema.py` | One-time: Neo4j indexes |
| `backend/src/library/graph/ingest.py` | `backend/` | `poetry run python src/library/graph/ingest.py` | One-time: embed + load data |
| `data/download.sh` | repo root | `bash data/download.sh` | Download PwC JSON dumps |
| `frontend/` | `frontend/` | `npm run dev` | Vite dev server |
| `docker-compose.yml` | repo root | `docker compose up --build` | Full stack via Docker |

---

## Environment Variables

| Prefix | Usage |
|--------|-------|
| `NEO4J_*` | Neo4j connection (URI, USER, PASSWORD) |
| `OPENAI_*` | OpenAI API key |
| `APP_*` | Application settings (ENV, LOG_LEVEL) |
| `ALLOWED_ORIGINS` | CORS allowed origins |
| `VITE_*` | Frontend environment variables (Vite-only) |

See `specs/system.md` for full env var reference and `.env.example` for template.

---

## Development Workflow

### First-time setup

```bash
# 1. Install backend deps (inside backend/)
cd backend
poetry install

# 2. Install frontend deps (inside frontend/)
cd ../frontend
npm install

# 3. Copy and fill env files
cp .env.example backend/.env         # Fill: NEO4J_PASSWORD, OPENAI_API_KEY, API_KEY
cp frontend/.env.example frontend/.env  # Fill: VITE_API_URL, VITE_API_KEY
```

### One-time data setup (run once per machine)

```bash
# 4. Start Neo4j container
docker compose up neo4j -d

# 5. Create indexes (from backend/)
cd backend && poetry run python src/library/graph/schema.py

# 6. Download PwC data
bash data/download.sh

# 7. Ingest data into Neo4j (~30 min for 5k papers)
cd backend && poetry run python src/library/graph/ingest.py
```

### Daily development

```bash
# Backend hot-reload (from backend/)
cd backend && poetry run uvicorn main:app --reload --port 8000

# Frontend dev server (from frontend/)
cd frontend && npm run dev     # → http://localhost:5173

# Run backend tests (from backend/)
cd backend && poetry run pytest tests/ -v

# OR: start everything via Docker Compose
docker compose up --build
```

---

## Documentation Structure

```
docs/
├── product/             # PRD, personas, user journeys, user stories, MVP scope
└── technical/
    ├── architecture.md  # System diagram
    ├── api-spec.md      # Endpoint contracts
    ├── data-model.md    # Neo4j schema
    └── adr/             # Architecture Decision Records
        ├── adr-001-neo4j-as-unified-store.md
        ├── adr-002-fastapi-over-django.md
        └── adr-003-shadcn-ui-over-alternatives.md

specs/
├── README.md
├── system.md
├── conventions/         # Coding conventions (this directory)
├── backend/             # Layer-by-layer implementation guides
└── frontend/            # Frontend implementation guides
```

---

## Original Template Reference

The following is the upstream `fastapi-service` template overview for reference:

### Purpose

`fastapi-service` is a production-ready FastAPI boilerplate for building modern Python web services. It provides a solid foundation with PostgreSQL for data storage, Redis for caching, structured logging, and best practices for API development.

### Template Structure

```
src/fastapi_service/
├── core/                   # Core functionality
│   ├── config.py          # Configuration (Pydantic Settings)
│   ├── logging.py         # Structured logging setup
│   ├── auth.py            # Authentication
│   └── dependencies.py    # FastAPI dependencies
├── modules/                # Feature modules
│   ├── health/
│   └── <your-module>/
│       ├── apiv1/handler.py
│       ├── usecase.py
│       ├── services.py
│       ├── repositories.py
│       ├── schemas.py
│       └── tasks.py       # Celery tasks (optional)
├── dbase/                 # Database layer (PostgreSQL)
├── shared/                # Shared utilities
│   ├── exceptions.py
│   └── utils/
├── main.py
├── router.py
└── worker.py              # Celery worker
```

### Key Files to Reference

- `pyproject.toml` — Poetry dependencies and scripts
- `Makefile` — Development and deployment commands
- `src/fastapi_service/main.py` — Application entry point
- `src/fastapi_service/router.py` — API router
