# Specs — graphrag-neo4j

Implementation guide for engineers building this project. These specs are the **"how to build it"** — not what to build (see `docs/`) or in what order (see `plan.md`).

---

## Directory Structure

```
specs/
├── README.md            ← You are here
├── system.md            ← Overall conventions: env vars, Docker, file layout, shared patterns
├── conventions/
│   ├── repository-overview.md       ← Project layout, tech stack, development workflow
│   ├── python-conventions.md        ← PEP 8, type hints, naming, imports, error handling
│   ├── python-module-structure.md   ← Module layering (Handler → UseCase → Service → Repo)
│   ├── testing.md                   ← Test structure: units / integrations / e2e mock / BDD
│   └── security.md                  ← X-API-Key authentication, CORS
├── backend/
│   ├── neo4j-models.md  ← neomodel OGM: BaseNode, StructuredNode, VectorIndex, repositories
│   ├── graph.md         ← Neo4j schema, neomodel models, constraints, vector indexes
│   ├── ingestion.md     ← Data ingestion: PwC JSON → parse → embed → load to Neo4j
│   ├── rag.md           ← RAG pipeline: embed query → vector search → traversal → LLM answer
│   └── api.md           ← FastAPI routes, Pydantic models, error handling, CORS
└── frontend/
    ├── components.md    ← React component structure, shadcn/ui usage, TypeScript props
    ├── state.md         ← State management: useState, useEffect, query state, types
    └── api-client.md    ← API client layer: fetch wrapper, TypeScript types, error handling
```

---

## How to Use These Specs

1. **Start with `system.md`** — understand env vars, project layout, Docker, and shared patterns.
2. **Read the relevant layer spec** before touching that layer's code.
3. **Check `conventions/`** for language/framework-level rules that apply across all files.
4. **Cross-reference `docs/technical/`** for the authoritative design decisions (architecture, data model, API spec).

---

## Quick Reference

| Topic | Spec | Key Files |
|-------|------|-----------|
| **Conventions** | | |
| Repo layout & workflow | `conventions/repository-overview.md` | `pyproject.toml`, `docker/docker-compose.dev.yml`, `Makefile` |
| Python style & patterns | `conventions/python-conventions.md` | All `.py` files in `graphrag_service/` |
| Module layering | `conventions/python-module-structure.md` | `graphrag_service/modules/graph/`, `graphrag_service/modules/rag/` |
| Tests | `conventions/testing.md` | `tests/unit/`, `tests/integration/`, `tests/e2e/*/bdd/` |
| Security (X-API-Key) | `conventions/security.md` | `graphrag_service/core/auth.py` |
| **System** | | |
| System-wide | `system.md` | `env.example`, `docker/docker-compose.dev.yml`, `graphrag_service/main.py` |
| **Backend** | | |
| Neo4j Models (neomodel) | `backend/neo4j-models.md` | `graphrag_service/dbase/neo4j/models/`, `graphrag_service/dbase/neo4j/client.py` |
| Neo4j Graph | `backend/graph.md` | `graphrag_service/modules/graph/services.py`, `graphrag_service/modules/graph/repositories.py` |
| Ingestion | `backend/ingestion.md` | `graphrag_service/modules/graph/services.py` (ingest_nodes, ingest_relationships) |
| RAG | `backend/rag.md` | `graphrag_service/modules/rag/services.py`, `graphrag_service/modules/rag/repositories.py` |
| API | `backend/api.md` | `graphrag_service/router.py`, `graphrag_service/main.py` |
| **Frontend** | | |
| Components | `frontend/components.md` | `src/components/` |
| State | `frontend/state.md` | `src/App.tsx` |
| API Client | `frontend/api-client.md` | `src/lib/api.ts`, `src/types/api.ts` |

---

## Related Documents

- [[projects/graphrag-neo4j/docs/technical/architecture]] — System architecture diagram
- [[projects/graphrag-neo4j/docs/technical/api-spec]] — API endpoint contract
- [[projects/graphrag-neo4j/docs/technical/data-model]] — Neo4j graph schema
- [[projects/graphrag-neo4j/plan]] — Implementation task order (15 tasks, 7 phases)
