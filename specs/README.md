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
│   └── security.md                  ← X-API-Key authentication, timing safety, CORS
├── backend/
│   ├── graph.md         ← Neo4j schema, Cypher patterns, constraints, vector indexes
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
| Repo layout & workflow | `conventions/repository-overview.md` | `pyproject.toml`, `docker-compose.yml` |
| Python style & patterns | `conventions/python-conventions.md` | All `.py` files |
| Module layering | `conventions/python-module-structure.md` | `library/rag/`, `library/graph/`, `modules/` |
| Tests | `conventions/testing.md` | `tests/unit/`, `tests/integration/`, `tests/e2e/*/bdd/` |
| Security (X-API-Key) | `conventions/security.md` | `core/security.py` |
| **System** | | |
| System-wide | `system.md` | `.env`, `docker-compose.yml`, `main.py` |
| **Backend** | | |
| Neo4j Graph | `backend/graph.md` | `library/graph/schema.py`, `library/graph/parser.py` |
| Ingestion | `backend/ingestion.md` | `library/graph/ingest.py` |
| RAG | `backend/rag.md` | `library/rag/embedder.py`, `library/rag/retriever.py`, `library/rag/generator.py` |
| API | `backend/api.md` | `router.py`, `main.py` |
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
