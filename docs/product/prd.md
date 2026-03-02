# Product Requirements Document — graphrag-neo4j

**Version:** 1.0
**Date:** 2026-03-02
**Status:** Approved
**Owner:** Lalu Erfandi Maula Yusnu

---

## 1. Problem Statement

Retrieval-Augmented Generation (RAG) systems built on vector similarity alone fail at relational reasoning. When a user asks *"What datasets are used by object detection methods introduced after 2018?"*, a traditional RAG system retrieves the most similar text chunks — it cannot traverse the relationships between methods, datasets, tasks, and papers.

The ML research space is inherently a **knowledge graph**: papers introduce methods, methods are applied to datasets, datasets benchmark tasks, tasks have subtasks. The structure is the meaning.

---

## 2. Goal

Build a full-stack **Graph RAG** demo that uses Neo4j as a unified graph + vector store, proving that graph-based retrieval enables multi-hop reasoning that pure vector search cannot. Target audience: the project serves as a portfolio showcase for ML/backend engineers.

---

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Answer quality | Answers cite specific entities from the graph (verifiable) |
| Multi-hop depth | At least 2-hop traversal demonstrated in example queries |
| Setup time | Reviewer can run the full stack in < 5 minutes via Docker Compose |
| Response latency | P90 < 5 seconds end-to-end |
| Graph size | ≥ 5,000 papers, ≥ 1,000 methods, ≥ 500 tasks, ≥ 500 datasets |
| Repo stars | Not a primary metric — quality > quantity |

---

## 4. Target Users

See [[docs/product/personas]] for full persona details.

- **Primary:** ML engineers and researchers exploring the demo
- **Secondary:** Technical recruiters and engineering managers evaluating the portfolio

---

## 5. Functional Requirements

### 5.1 Query Interface
- **FR-01:** User can type a natural language question about ML research
- **FR-02:** System returns a grounded answer within 10 seconds
- **FR-03:** System shows which graph nodes were retrieved as seed nodes
- **FR-04:** System shows the full Cypher query used for retrieval (expandable panel)
- **FR-05:** Pre-seeded example questions are available as quick-start buttons

### 5.2 Graph Visualization
- **FR-06:** Retrieved subgraph is rendered as an interactive force-directed graph
- **FR-07:** Seed nodes are visually distinct (different color/size) from traversed nodes
- **FR-08:** Node type is visually encoded (Paper, Method, Task, Dataset each have a color)
- **FR-09:** Edge labels show relationship types (INTRODUCES, APPLIED_ON, etc.)
- **FR-10:** User can drag, zoom, and pan the graph

### 5.3 Knowledge Graph
- **FR-11:** Graph contains Papers, Methods, Tasks, Datasets as node types
- **FR-12:** Graph contains semantic relationships (INTRODUCES, APPLIES_ON, EVALUATED_ON, USED_FOR, VARIANT_OF)
- **FR-13:** Each node stores an embedding vector for semantic search
- **FR-14:** Vector similarity search and graph traversal are performed in a single Neo4j query

### 5.4 API
- **FR-15:** `POST /api/query` accepts a question and returns answer + subgraph
- **FR-16:** `GET /api/graph/schema` returns available node labels and relationship types
- **FR-17:** `GET /api/graph/explore` returns a sample of the graph for exploration
- **FR-18:** `GET /api/health` returns system health including Neo4j connection status

---

## 6. Non-Functional Requirements

| Requirement | Specification |
|-------------|--------------|
| **Performance** | API response < 10s P90 (embedding + traversal + LLM) |
| **Reliability** | Neo4j connection retry on startup |
| **Portability** | Full stack runnable via `docker compose up` on any machine |
| **Developer experience** | Hot-reload in both backend and frontend in dev mode |
| **Cost** | OpenAI API usage < $5 per full data ingestion run |
| **Data size** | Curated subset: 5,000 papers (not full PwC dataset) |
| **Security** | API keys only via environment variables, never hardcoded |

---

## 7. Data Source

**Papers With Code** (paperswithcode.com) provides free JSON dumps:
- Free, openly licensed
- Pre-structured relationships (no inference needed)
- Domain-recognizable to any ML engineer

---

## 8. Out of Scope (v1)

- User authentication or session management
- Persistent chat history
- Real-time streaming responses
- Fine-tuned LLM (OpenAI API only)
- Full Papers With Code dataset (5k paper subset only)
- Mobile-responsive design
- Multi-language support
