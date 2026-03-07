---
created: 2026-03-02
updated: 2026-03-07
source: https://raw.githubusercontent.com/nunenuh/sdd-python-service/refs/heads/main/specs/conventions/00-repository-overview.md
---

# Repository Overview

> **Project Mapping**: This document describes the `graphrag-neo4j` repository structure,
> adapted from the `fastapi-service` template. See the Original Template Reference at the bottom
> for the upstream structure.

---

## graphrag-neo4j Repository Structure

Root is minimal — only infrastructure files. Each service (`backend/`, `frontend/`) is **fully independent** with its own dependency manager, Dockerfile, and `.env`.

```
graphrag-neo4j/                  # Root — GitHub repo root
├── docker/
│   └── docker-compose.dev.yml   # Orchestrates all services (dev)
├── env.example                  # Template for root-level secrets (Neo4j, OpenAI, APP_X_API_KEY)
├── Makefile                     # Top-level commands (make backend, make frontend, make dev)
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

Has its own Poetry setup, Dockerfile, and tests. All Python source lives in `backend/src/graphrag_service/` as a proper Python package. No Python tooling at repo root.

```
backend/
├── pyproject.toml               # Poetry: deps + tool config
│                                #   packages = [{include = "graphrag_service", from = "src"}]
│                                #   scripts: start, dev, cli
├── poetry.toml                  # Poetry local config
├── poetry.lock
├── Dockerfile                   # Multi-stage: build -> runtime image
├── .env                         # Local dev (not committed — copy from root env.example)
│
├── src/
│   └── graphrag_service/        # <- ALL Python source lives here (proper package)
│       ├── __init__.py
│       ├── main.py              # FastAPI app factory, CORS, uvicorn entry points
│       ├── router.py            # Aggregates module routers: /api/v1/health, /api/v1/graph, /api/v1/rag
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Pydantic Settings + get_settings() with @lru_cache
│       │   ├── auth.py          # X-API-Key dependency (APP_X_API_KEY env var)
│       │   └── logging.py       # structlog setup, get_logger(__name__)
│       │
│       ├── dbase/               # Database layer
│       │   ├── __init__.py
│       │   └── neo4j/
│       │       ├── __init__.py
│       │       ├── client.py    # Neo4j driver wrapper (run_query)
│       │       └── models/      # neomodel OGM definitions
│       │           ├── __init__.py
│       │           ├── base.py
│       │           ├── nodes.py
│       │           └── relationships.py
│       │
│       ├── shared/              # Shared utilities and services
│       │   ├── __init__.py
│       │   ├── exceptions.py    # Custom exception classes
│       │   ├── utils/           # Utility functions
│       │   └── services/        # Shared service classes
│       │
│       ├── cli/                 # Typer-based CLI
│       │   ├── __init__.py
│       │   ├── base.py          # CLI base setup
│       │   └── main.py          # CLI entry point (aggregates module commands)
│       │
│       └── modules/             # Feature modules (Handler -> UseCase -> Service -> Repository)
│           ├── __init__.py
│           ├── health/          # Health check module
│           │   ├── __init__.py
│           │   └── apiv1/
│           │       ├── __init__.py
│           │       └── handler.py
│           │
│           ├── graph/           # Graph schema, parsing, ingestion, exploration
│           │   ├── __init__.py
│           │   ├── schemas.py       # Pydantic request/response models
│           │   ├── usecase.py       # Orchestration layer
│           │   ├── services.py      # Business logic
│           │   ├── repositories.py  # Data access
│           │   ├── apiv1/
│           │   │   ├── __init__.py
│           │   │   └── handler.py   # FastAPI routes for graph
│           │   └── cli/
│           │       ├── __init__.py
│           │       └── commands.py  # Typer CLI commands for graph
│           │
│           └── rag/             # RAG pipeline: embed, retrieve, generate
│               ├── __init__.py
│               ├── schemas.py       # Pydantic request/response models
│               ├── usecase.py       # Orchestration layer
│               ├── services.py      # Business logic
│               ├── repositories.py  # Data access
│               └── apiv1/
│                   ├── __init__.py
│                   └── handler.py   # FastAPI routes for RAG
│
└── tests/                       # All Python tests
    ├── conftest.py              # Shared fixtures
    ├── unit/                    # Unit tests — mirrors src/ structure
    │   ├── conftest.py
    │   ├── modules/
    │   │   ├── rag/
    │   │   └── graph/
    │   ├── core/
    │   │   └── test_config.py
    │   └── dbase/
    │       └── neo4j/
    │           └── test_client.py
    ├── integration/             # Integration tests — real Neo4j
    │   ├── conftest.py          # Real Neo4j test client
    │   └── modules/
    │       └── graph/
    └── e2e/
        ├── query/
        ├── graph/
        └── health/
```

**`graphrag_service` is the Python package root.** All imports use the full package name:
```python
from graphrag_service.core.config import get_settings     # config with @lru_cache
from graphrag_service.core.auth import verify_api_key      # APP_X_API_KEY auth
from graphrag_service.core.logging import get_logger       # structlog logger
from graphrag_service.modules.graph.usecase import GraphUseCase
from graphrag_service.modules.rag.services import RAGService
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models.nodes import Paper
```

**Module structure convention** (`modules/{name}/`) follows the Handler -> UseCase -> Service -> Repository pattern. See [[projects/graphrag-neo4j/specs/conventions/python-module-structure]] for full detail.

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
| Graph + Vector DB     | Neo4j 5.x / 6.x Community                       |
| Neo4j Driver          | neo4j ^6.1.0                                     |
| OGM                   | neomodel                                         |
| Logging               | structlog                                        |
| CLI                   | Typer + Rich                                     |
| Frontend              | Vite + React + TypeScript + Tailwind + shadcn/ui |
| LLM                   | OpenAI GPT-4o-mini                               |
| Embeddings            | OpenAI text-embedding-3-small (1536 dims)        |
| Visualization         | react-force-graph-2d                             |
| Infra                 | Docker Compose                                   |
| Data                  | Papers With Code (5k paper subset)               |
| Dependency Management | Poetry (backend), npm (frontend)                 |

### Key Dependencies (backend)

| Package    | Purpose                          |
| ---------- | -------------------------------- |
| neo4j      | Neo4j Bolt driver (^6.1.0)       |
| neomodel   | Neo4j OGM for node/rel models    |
| structlog  | Structured logging               |
| typer      | CLI framework                    |
| rich       | Terminal formatting              |
| tqdm       | Progress bars                    |
| psutil     | System resource monitoring       |

---

## Architecture Pattern

`graphrag-neo4j` follows a proper layered architecture with clear separation of concerns:

```
API Handler (modules/{name}/apiv1/handler.py)
    |
UseCase (modules/{name}/usecase.py)
    |
Service (modules/{name}/services.py)
    |
Repository (modules/{name}/repositories.py)
    |
Neo4j Client (dbase/neo4j/client.py) + neomodel OGM (dbase/neo4j/models/)
    |
Neo4j Database
```

### Router Aggregation

`router.py` aggregates all module routers under versioned prefixes:

| Prefix           | Module  | Purpose                              |
| ---------------- | ------- | ------------------------------------ |
| `/api/v1/health` | health  | Health check                         |
| `/api/v1/graph`  | graph   | Graph schema, ingestion, exploration |
| `/api/v1/rag`    | rag     | RAG query pipeline                   |

### Layer Mapping

| Layer        | Location                              | Responsibility                    |
| ------------ | ------------------------------------- | --------------------------------- |
| Handler      | `modules/{name}/apiv1/handler.py`     | FastAPI routes, request/response  |
| UseCase      | `modules/{name}/usecase.py`           | Orchestration, workflow logic     |
| Service      | `modules/{name}/services.py`          | Business logic                    |
| Repository   | `modules/{name}/repositories.py`      | Data access abstraction           |
| DB Client    | `dbase/neo4j/client.py`               | Neo4j driver wrapper              |
| OGM Models   | `dbase/neo4j/models/`                 | neomodel node/relationship defs   |

---

## Key Patterns

1. **Layered Architecture**: Handler -> UseCase -> Service -> Repository -> Neo4j Client/OGM
2. **Configuration**: `get_settings()` with `@lru_cache` from `core/config.py` (not a bare singleton)
3. **Authentication**: `core/auth.py` with `APP_X_API_KEY` environment variable
4. **Structured Logging**: `structlog` via `core/logging.py`, usage: `get_logger(__name__)`
5. **Graph Pattern**: All data access via parameterized Cypher — never string interpolation
6. **Immutability**: All transform functions return new dicts, never mutate inputs
7. **Batch Processing**: OpenAI embeddings in batches of 100, Neo4j writes via `UNWIND`
8. **CLI per Module**: Each module can expose Typer commands in `modules/{name}/cli/commands.py`

---

## Entry Points

| Entry Point | Command | Purpose |
|------------|---------|---------|
| FastAPI server | `poetry run start` | Uvicorn production server (port 8005) |
| FastAPI dev server | `poetry run dev` | Uvicorn with reload (port 8005) |
| Typer CLI | `poetry run cli` | CLI commands (graph ingestion, etc.) |
| Makefile (backend) | `make backend` | Start backend via Makefile |
| Makefile (frontend) | `make frontend` | Start frontend via Makefile |
| Makefile (all) | `make dev` | Start full stack via Makefile |
| Frontend dev | `npm run dev` (in `frontend/`) | Vite dev server (port 5173) |
| Docker Compose | `docker compose -f docker/docker-compose.dev.yml up --build` | Full stack via Docker |

### Poetry Script Definitions (pyproject.toml)

```toml
[tool.poetry.scripts]
start = "graphrag_service.main:main"
dev = "graphrag_service.main:dev"
cli = "graphrag_service.cli.main:main"
```

### Package Configuration (pyproject.toml)

```toml
[tool.poetry]
packages = [{include = "graphrag_service", from = "src"}]
```

---

## Environment Variables

| Prefix       | Usage                                            |
| ------------ | ------------------------------------------------ |
| `NEO4J_*`    | Neo4j connection (URI, USER, PASSWORD)           |
| `OPENAI_*`   | OpenAI API key                                   |
| `APP_*`      | Application settings (ENV, LOG_LEVEL, X_API_KEY) |
| `ALLOWED_ORIGINS` | CORS allowed origins                        |
| `VITE_*`     | Frontend environment variables (Vite-only)       |

The env template is at the repo root: `env.example` (not `.env.example`).

See `specs/system.md` for full env var reference.

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
cp env.example backend/.env         # Fill: NEO4J_PASSWORD, OPENAI_API_KEY, APP_X_API_KEY
cp frontend/.env.example frontend/.env  # Fill: VITE_API_URL, VITE_API_KEY
```

### One-time data setup (run once per machine)

```bash
# 4. Start Neo4j container
docker compose -f docker/docker-compose.dev.yml up neo4j -d

# 5. Download PwC data
bash data/download.sh

# 6. Ingest data into Neo4j via CLI
cd backend && poetry run cli graph ingest
```

### Daily development

```bash
# Backend with hot-reload (from backend/)
cd backend && poetry run dev        # -> http://localhost:8005

# Frontend dev server (from frontend/)
cd frontend && npm run dev          # -> http://localhost:5173

# Run backend tests (from backend/)
cd backend && poetry run pytest tests/ -v

# OR: use Makefile from repo root
make dev                            # Start full stack

# OR: start everything via Docker Compose
docker compose -f docker/docker-compose.dev.yml up --build
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
src/graphrag_service/              # Was src/fastapi_service/ in the template
├── core/                   # Core functionality
│   ├── config.py          # Configuration (Pydantic Settings + @lru_cache)
│   ├── logging.py         # Structured logging setup (structlog)
│   ├── auth.py            # Authentication (X-API-Key)
│   └── dependencies.py    # FastAPI dependencies
├── modules/                # Feature modules
│   ├── health/
│   └── <your-module>/
│       ├── apiv1/handler.py
│       ├── usecase.py
│       ├── services.py
│       ├── repositories.py
│       ├── schemas.py
│       ├── cli/commands.py # Typer CLI commands (optional)
│       └── tasks.py       # Celery tasks (optional)
├── dbase/                 # Database layer (Neo4j in graphrag-neo4j)
│   └── neo4j/
│       ├── client.py
│       └── models/        # neomodel OGM
├── shared/                # Shared utilities
│   ├── exceptions.py
│   ├── utils/
│   └── services/
├── cli/                   # Typer CLI entry point
│   ├── base.py
│   └── main.py
├── main.py
├── router.py
└── worker.py              # Celery worker (not used in graphrag-neo4j)
```

### Key Files to Reference

- `pyproject.toml` — Poetry dependencies, scripts (`start`, `dev`, `cli`), and package config
- `Makefile` — Development and deployment commands
- `src/graphrag_service/main.py` — Application entry point
- `src/graphrag_service/router.py` — API router (aggregates `/api/v1/health`, `/api/v1/graph`, `/api/v1/rag`)
- `src/graphrag_service/cli/main.py` — Typer CLI entry point
