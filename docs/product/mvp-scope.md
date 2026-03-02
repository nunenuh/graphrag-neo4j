# MVP Scope — graphrag-neo4j

**Date:** 2026-03-02
**Version:** v1.0

---

## What is the MVP?

The MVP is the smallest version of graphrag-neo4j that clearly demonstrates Graph RAG is better than traditional RAG, runs in one command, and is worth putting on a portfolio.

---

## MVP Definition of Done

- [ ] User can ask a natural language question about ML research
- [ ] System retrieves a subgraph (vector search + graph traversal) in Neo4j
- [ ] LLM generates a grounded answer from the subgraph
- [ ] Interactive graph visualization shows the retrieved subgraph
- [ ] Cypher panel shows the query used
- [ ] Full stack runs via `docker compose up`
- [ ] README explains the Graph RAG concept and setup

---

## In Scope (v1)

| Feature | Priority |
|---------|----------|
| Natural language query input | Must Have |
| Vector seed node retrieval (Neo4j vector index) | Must Have |
| Graph traversal from seed nodes (depth 1–2) | Must Have |
| LLM answer generation (GPT-4o-mini) | Must Have |
| Interactive force-directed graph visualization | Must Have |
| Color-coded node types (Paper/Method/Task/Dataset) | Must Have |
| Seed node highlighting (orange) | Must Have |
| Cypher query panel (collapsible) | Must Have |
| Example questions (4 pre-seeded) | Must Have |
| FastAPI backend with `/api/query`, `/api/health` | Must Have |
| React + Vite + Tailwind + shadcn/ui frontend | Must Have |
| Docker Compose setup (Neo4j + backend + frontend) | Must Have |
| Papers With Code data (5k paper subset) | Must Have |
| Latency display | Should Have |
| `/api/graph/explore` endpoint | Should Have |
| `/api/graph/schema` endpoint | Should Have |

---

## Out of Scope (v1 → future)

| Feature | Why Deferred |
|---------|-------------|
| User authentication | Portfolio demo — no need |
| Persistent chat history | Adds DB complexity, not core value |
| Streaming LLM responses | Nice UX, not core value |
| Fine-tuned LLM | Out of budget |
| Full PwC dataset (300k+ papers) | Cost + time (5k subset proves the concept) |
| Mobile responsive design | Desktop demo is sufficient |
| Multiple conversation threads | Single-question demo is cleaner |
| Graph database admin UI | Neo4j Browser already handles this |
| User feedback / rating system | Not needed for portfolio |

---

## Phase Roadmap

### v1.0 — MVP (now)
Core Graph RAG: query → seed nodes → traversal → answer + graph visualization

### v2.0 — Enhanced UX
- Streaming responses (SSE)
- Persistent conversation history (follow-up questions)
- Node click → sidebar with full node details
- Graph filtering by node type

### v3.0 — Expanded Knowledge
- Full Papers With Code dataset
- Add `:Author` nodes and `:AUTHORED_BY` relationships
- Citation graph (`Paper -[:CITES]-> Paper`)
- Time-filtered queries ("methods from 2022 onwards")
