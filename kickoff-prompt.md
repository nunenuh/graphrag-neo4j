# AI Kickoff Prompt — graphrag-neo4j

> Copy the block below and paste it as your first message when starting the implementation session.

---


You are implementing the `graphrag-neo4j` project — a full-stack Graph RAG portfolio system.

REQUIRED SKILL: Use `superpowers:executing-plans` to implement the plan task-by-task.

---

## Project Locations

- **Code repo (where you write code):** `~/projects/graphrag-neo4j/`
- **Documentation vault (read-only reference):** `~/vaults/projects/graphrag-neo4j/`

The vault contains all specs, docs, and the implementation plan. The code goes in the separate repo directory.

---

## Your Primary Reference: The Implementation Plan

Read this first:
`~/vaults/projects/graphrag-neo4j/plan.md`

It has 15 tasks across 7 phases. Execute them in order. Each task has:
- Exact files to create
- Complete code to write
- Exact shell commands to run
- A commit at the end

---

## Critical Structure Rules (read before writing any code)

### Backend layout (ALL Python lives under `backend/src/`)

```
backend/
├── pyproject.toml          # Poetry — NOT pip/requirements.txt
├── Dockerfile
└── src/                    # pythonpath = ["src"] — imports start here
    ├── main.py
    ├── router.py           # All API routes + Pydantic models
    ├── core/
    │   ├── config.py       # Pydantic Settings
    │   └── security.py     # X-API-Key
    ├── dbase/
    │   └── neo4j/
    │       └── client.py   # Neo4j driver wrapper
    ├── library/
    │   ├── graph/
    │   │   ├── schema.py   # CREATE CONSTRAINT / CREATE INDEX
    │   │   ├── parser.py   # PwC JSON → entity dicts
    │   │   └── ingest.py   # parse → embed → load orchestrator
    │   └── rag/
    │       ├── embedder.py
    │       ├── retriever.py
    │       └── generator.py
    └── modules/            # future feature modules
```

### Tests mirror src/
```
backend/tests/
├── unit/library/rag/       # mocked OpenAI + Neo4j
├── unit/library/graph/
├── unit/dbase/neo4j/
├── integration/library/graph/  # real Neo4j test instance
└── e2e/query/mock/         # full API tests, mocked services
    e2e/query/bdd/          # pytest-bdd, real services
```

### Import style (pythonpath = ["src"])
```python
from core.config import settings
from dbase.neo4j.client import Neo4jClient
from library.rag.embedder import batch_embed
from library.graph.parser import parse_papers
```

### Key conventions
- **Dependency injection**: Pass `Neo4jClient` as a parameter — no module-level singletons
- **Immutability**: Return new dicts, never mutate inputs (`{**entity, "embedding": emb}`)
- **Batch writes**: `UNWIND $list` — never one Cypher per record
- **Poetry**: `poetry run python src/...` — never bare `python`
- **Type hints**: Required on all function signatures (Python 3.11 style: `list[str]`, `dict | None`)
- **Error handling**: Explicit typed exceptions, never silent swallows
- **Logging**: `logger = logging.getLogger(__name__)` per file, `extra={}` for context

---

## Supporting Specs

If plan.md doesn't cover something in enough detail, read the relevant spec:

| Topic | Spec file |
|-------|-----------|
| Repo layout, dev workflow | `specs/conventions/repository-overview.md` |
| Python style, naming, imports | `specs/conventions/python-conventions.md` |
| Module layering (Handler→UseCase→Repo) | `specs/conventions/python-module-structure.md` |
| Test structure, BDD patterns | `specs/conventions/testing.md` |
| X-API-Key auth | `specs/conventions/security.md` |
| Neo4j schema + Cypher patterns | `specs/backend/graph.md` |
| Ingestion pipeline | `specs/backend/ingestion.md` |
| RAG pipeline | `specs/backend/rag.md` |
| FastAPI routes, Pydantic models | `specs/backend/api.md` |
| React components, shadcn/ui | `specs/frontend/components.md` |
| State management | `specs/frontend/state.md` |
| API client (TypeScript) | `specs/frontend/api-client.md` |
| System (env vars, Docker) | `specs/system.md` |

All spec files are in `~/vaults/projects/graphrag-neo4j/specs/`.

---

## Tech Stack Summary

| Layer | Tech |
|-------|------|
| Graph + Vector DB | Neo4j 5.15 Community |
| Backend | FastAPI + Python 3.11 + Poetry |
| Frontend | Vite + React 18 + TypeScript + Tailwind + shadcn/ui |
| LLM + Embeddings | OpenAI GPT-4o-mini + text-embedding-3-small (1536-dim) |
| Visualization | react-force-graph-2d |
| Infra | Docker Compose |
| Data | Papers With Code (~5k paper subset) |

---

## What the System Does

Users ask natural language questions about ML research.
The system:
1. Embeds the question → vector
2. Searches Neo4j vector indexes → seed nodes (Papers, Methods, Tasks, Datasets)
3. Traverses graph edges from seed nodes → subgraph
4. Serializes subgraph as structured text → LLM context
5. GPT-4o-mini generates grounded answer

Frontend shows: chat answer + interactive force graph + raw Cypher used.

---

## Now start implementing

Use `superpowers:executing-plans` and begin with Task 1 from `plan.md`.
