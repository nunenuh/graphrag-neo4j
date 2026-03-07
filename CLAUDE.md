# CLAUDE.md — graphrag-neo4j

## Project

Full-stack **Graph RAG** system using Neo4j as unified graph + vector store.
Natural language questions about ML research landscape — retrieves knowledge subgraph, generates grounded answers.

```
Question → Embed → Vector Search (seed nodes) → 2-hop Graph Traverse → LLM Answer (grounded)
```

## Current State

- **Phase**: Phase 1 complete (backend). Frontend not yet started.
- **Branch**: `dev` (all work happens here; `main` is production)
- **Backend**: Fully implemented — all 8 API endpoints, CLI, ingestion pipeline, RAG pipeline
- **Frontend**: Specs written, no code yet
- **Tests**: 143 unit tests, 74% coverage. Integration/E2E not yet written.
- **Data**: Papers With Code (Paper, Method, Task, Dataset nodes)

## Architecture

```
Handler (FastAPI/CLI) → UseCase → Service → Repository → Neo4j Client/OGM → Neo4j DB
```

Each module in `backend/src/graphrag_service/modules/{name}/` follows this layering.

## Key Paths

| Path | What |
|------|------|
| `backend/src/graphrag_service/` | All backend Python source |
| `backend/tests/` | All tests (unit/integration/e2e) |
| `frontend/` | React + Vite app (not yet implemented) |
| `docker/` | Docker Compose files (dev, run) |
| `data/` | PwC JSON data + download script |
| `env.example` | Environment variable template |
| `Makefile` | All project commands (`make help`) |

## Specs (read before implementing)

| Spec | When to Read |
|------|-------------|
| `specs/system.md` | Env vars, Docker, project layout, shared patterns |
| `specs/conventions/repository-overview.md` | Full repo structure, tech stack, architecture pattern |
| `specs/conventions/python-conventions.md` | Python style: PEP 8, type hints, naming, imports |
| `specs/conventions/python-module-structure.md` | Module layering: Handler → UseCase → Service → Repo |
| `specs/conventions/testing.md` | Test structure: unit / integration / e2e / BDD |
| `specs/conventions/security.md` | X-API-Key auth, CORS |
| `specs/conventions/git-workflow.md` | Git branch/commit/PR workflow (issue-driven) |
| `specs/backend/neo4j-models.md` | neomodel OGM: BaseNode, StructuredNode, VectorIndex |
| `specs/backend/graph.md` | Neo4j schema, models, constraints, vector indexes |
| `specs/backend/ingestion.md` | Data ingestion: PwC JSON → parse → embed → Neo4j |
| `specs/backend/rag.md` | RAG pipeline: embed → vector search → traverse → LLM |
| `specs/backend/api.md` | FastAPI routes, Pydantic models, error handling |
| `specs/backend/llm.md` | LangChain providers, embeddings, chat, LangGraph |
| `specs/backend/test-gaps.md` | 116 missing edge/corner case tests (deferred) |
| `specs/frontend/components.md` | React components, shadcn/ui, TypeScript props |
| `specs/frontend/state.md` | State management: useState, hooks, types |
| `specs/frontend/api-client.md` | API client layer: fetch wrapper, types, errors |

## Docs (design decisions)

| Doc | What |
|-----|------|
| `docs/product/prd.md` | Product requirements |
| `docs/product/mvp-scope.md` | MVP scope definition |
| `docs/technical/architecture.md` | System architecture |
| `docs/technical/api-spec.md` | API endpoint contract |
| `docs/technical/data-model.md` | Neo4j graph schema |
| `docs/technical/adr/` | Architecture Decision Records (3 ADRs) |
| `docs/comparison-with-full-spec.md` | Gap analysis: our product vs full GraphRAG spec |
| `docs/backend-layout-full-spec.md` | Future backend layout for full spec (Phase 2+) |

## Git Workflow

**All work is issue-driven.** See `specs/conventions/git-workflow.md` for full details.

```
1. Pick issue
2. git checkout dev && git pull && git checkout -b feat/<issue-id>-<slug>
3. git push -u origin feat/<issue-id>-<slug>
4. Do the work (code → tests; frontend: code → review → agree → tests)
5. Create PR targeting dev
6. Review → merge → git checkout dev && git pull && git fetch --all
```

**Commit format**: `<type>(<scope>): <description> #<issue-id>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

## API Endpoints (Phase 1)

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/health/ping` | No |
| `GET` | `/api/v1/health/status` | No |
| `GET` | `/api/v1/graph/schema` | X-API-Key |
| `GET` | `/api/v1/graph/explore?limit=50` | X-API-Key |
| `GET` | `/api/v1/graph/stats` | X-API-Key |
| `GET` | `/api/v1/graph/nodes/{uid}` | X-API-Key |
| `GET` | `/api/v1/graph/search?q=...` | X-API-Key |
| `POST` | `/api/v1/rag/query` | X-API-Key |

## Commands

```bash
make help              # Show all commands
make setup             # First-time setup (env + deps)
make neo4j             # Start Neo4j container
make schema            # Create Neo4j constraints + vector indexes
make download          # Download PwC data
make ingest            # Ingest data into Neo4j
make dev               # Start backend (8005) + frontend (5173)
make test-unit         # Run unit tests
make test-coverage     # Tests with coverage report
make lint              # Syntax checks
make format            # Auto-format with black + isort
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python 3.11 + LangGraph + LangChain |
| Graph + Vector DB | Neo4j 5.x (neomodel OGM) |
| LLM | Provider-agnostic: OpenAI, Google, Ollama, Qwen |
| Embeddings | Provider-agnostic (default: text-embedding-3-small, 1536 dims) |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui |
| Visualization | react-force-graph-2d |
| Infra | Docker Compose |

## What's Next

1. **Frontend implementation** — build React app per `specs/frontend/` specs
2. **Integration tests** — real Neo4j tests
3. **E2E tests** — full API flow tests
4. **Phase 2+** — full GraphRAG spec (see `docs/comparison-with-full-spec.md`)
