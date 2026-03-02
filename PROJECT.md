# graphrag-neo4j

**Status:** Planning
**Goal:** Full-stack Graph RAG portfolio project — ML knowledge graph over Papers With Code data, using Neo4j as unified graph + vector store.
**Repo:** `github.com/nunenuh/graphrag-neo4j`

---

## Key Documents

### Product
- [[projects/graphrag-neo4j/docs/product/prd]] — Product Requirements Document
- [[projects/graphrag-neo4j/docs/product/personas]] — User Personas
- [[projects/graphrag-neo4j/docs/product/user-journeys]] — User Journey Maps
- [[projects/graphrag-neo4j/docs/product/user-stories]] — User Stories & Acceptance Criteria
- [[projects/graphrag-neo4j/docs/product/mvp-scope]] — MVP Scope & Roadmap

### Technical
- [[projects/graphrag-neo4j/docs/technical/architecture]] — System Architecture
- [[projects/graphrag-neo4j/docs/technical/api-spec]] — API Specification
- [[projects/graphrag-neo4j/docs/technical/data-model]] — Neo4j Graph Schema & Data Model
- [[projects/graphrag-neo4j/docs/technical/adr/adr-001-neo4j-as-unified-store]] — ADR: Why Neo4j for both graph + vector
- [[projects/graphrag-neo4j/docs/technical/adr/adr-002-fastapi-over-django]] — ADR: Why FastAPI
- [[projects/graphrag-neo4j/docs/technical/adr/adr-003-shadcn-ui-over-alternatives]] — ADR: Why shadcn/ui

### Planning
- [[projects/graphrag-neo4j/design]] — System Design (approved)
- [[projects/graphrag-neo4j/plan]] — Implementation Plan (15 tasks, 7 phases)

### Specs (Implementation Guide)
- [[projects/graphrag-neo4j/specs/README]] — Specs directory overview
- [[projects/graphrag-neo4j/specs/system]] — System conventions: env vars, Docker, shared patterns

**Conventions**
- [[projects/graphrag-neo4j/specs/conventions/repository-overview]] — Repo layout, stack, dev workflow
- [[projects/graphrag-neo4j/specs/conventions/python-conventions]] — PEP 8, type hints, naming, logging
- [[projects/graphrag-neo4j/specs/conventions/python-module-structure]] — Module layering (Handler → UseCase → Service → Repo)
- [[projects/graphrag-neo4j/specs/conventions/testing]] — Test structure: units / integrations / e2e mock / BDD (real)
- [[projects/graphrag-neo4j/specs/conventions/security]] — X-API-Key auth, timing safety, CORS

**Backend**
- [[projects/graphrag-neo4j/specs/backend/graph]] — Neo4j schema, Cypher patterns, parser
- [[projects/graphrag-neo4j/specs/backend/ingestion]] — PwC data ingestion pipeline
- [[projects/graphrag-neo4j/specs/backend/rag]] — RAG pipeline: embed → retrieve → generate
- [[projects/graphrag-neo4j/specs/backend/api]] — FastAPI routes, Pydantic models

**Frontend**
- [[projects/graphrag-neo4j/specs/frontend/components]] — React components, shadcn/ui usage
- [[projects/graphrag-neo4j/specs/frontend/state]] — State management patterns
- [[projects/graphrag-neo4j/specs/frontend/api-client]] — API client, TypeScript types

---

## Stack
| Layer             | Tech                                          |
| ----------------- | --------------------------------------------- |
| Graph + Vector DB | Neo4j 5.15                                    |
| Backend           | FastAPI + Python 3.11                         |
| Frontend          | React + Vite + TypeScript + Tailwind + shadcn |
| LLM + Embeddings  | OpenAI GPT-4o-mini + text-embedding-3-small   |
| Visualization     | react-force-graph-2d                          |
| Infra             | Docker Compose                                |
| Data              | Papers With Code (5k paper subset)            |
