# System Architecture — graphrag-neo4j

**Date:** 2026-03-02
**Status:** Approved

---

## Overview

Three-tier architecture: Vite + React frontend → FastAPI backend → Neo4j graph + vector database.

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│        Vite + React + Tailwind + shadcn/ui (port 5173)      │
│   ChatPanel │ GraphViewer │ CypherPanel                     │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP (JSON)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│              FastAPI / Python 3.11 (port 8000)              │
│                                                             │
│  router.py                                                  │
│       │                                                     │
│       ├── library/rag/embedder.py → OpenAI text-embedding-3-small │
│       ├── library/rag/retriever.py → vector search + traversal    │
│       └── library/rag/generator.py → OpenAI GPT-4o-mini          │
└────────────────────┬────────────────────────────────────────┘
                     │ Bolt protocol (port 7687)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATABASE                               │
│            Neo4j 5.15 Community (port 7474/7687)            │
│                                                             │
│  (:Paper)    (:Method)    (:Task)    (:Dataset)             │
│      │           │           │           │                  │
│   embedding   embedding  embedding   embedding              │
│   (float[1536] per node — stored on node property)         │
│                                                             │
│  Vector Indexes: paper_embeddings, method_embeddings, ...   │
│  Relationships: INTRODUCES, APPLIED_ON, EVALUATED_ON, ...   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
              OpenAI API (external)
              - text-embedding-3-small (ingestion + query time)
              - gpt-4o-mini (answer generation)
```

---

## Graph RAG Pipeline

```
1. EMBED QUERY
   question: str
   → OpenAI text-embedding-3-small
   → query_vector: float[1536]

2. VECTOR SEARCH (seed nodes)
   CALL db.index.vector.queryNodes('method_embeddings', 5, $query_vector)
   CALL db.index.vector.queryNodes('task_embeddings', 5, $query_vector)
   CALL db.index.vector.queryNodes('paper_embeddings', 5, $query_vector)
   CALL db.index.vector.queryNodes('dataset_embeddings', 5, $query_vector)
   → top-k seed nodes by cosine similarity

3. GRAPH TRAVERSAL
   MATCH (seed)-[r1]->(n1)
   OPTIONAL MATCH (n1)-[r2]->(n2)
   WHERE seed.id IN $seed_ids
   → subgraph: nodes + edges (depth 1-2)

4. CONTEXT SERIALIZATION
   → structured text: "{entity} -[RELATIONSHIP]-> {entity}"
   → passed to LLM as context

5. ANSWER GENERATION
   → GPT-4o-mini with system prompt + subgraph context + question
   → grounded natural language answer

6. RESPONSE
   → answer + seed_nodes + subgraph (nodes + edges) + cypher_used + latency_ms
```

---

## Data Flow: Ingestion

```
Papers With Code JSON (data/)
        │
        ├── papers.json    → (:Paper)   nodes
        ├── methods.json   → (:Method)  nodes
        ├── tasks.json     → (:Task)    nodes
        ├── datasets.json  → (:Dataset) nodes
        └── evaluations.json → relationships
                │
                ▼
        library/graph/parser.py (clean + normalize)
                │
                ▼
        library/rag/embedder.py (OpenAI batch embed, batch_size=100)
                │
                ▼
        Neo4j (MERGE nodes + SET embedding property)
                │
                ▼
        Neo4j Vector Indexes (created once via library/graph/schema.py)
```

---

## Module Responsibility

| Module | Responsibility |
|--------|---------------|
| `core/config.py` | All settings from environment variables |
| `core/security.py` | X-API-Key authentication dependency |
| `dbase/neo4j/client.py` | Neo4j connection, run_query |
| `library/graph/schema.py` | Create constraints and vector indexes |
| `library/graph/parser.py` | Parse PwC JSON into clean entity dicts |
| `library/graph/ingest.py` | Orchestrate parsing + embedding + loading |
| `library/rag/embedder.py` | OpenAI embedding (single + batch) |
| `library/rag/retriever.py` | Vector search → seed nodes → graph traversal |
| `library/rag/generator.py` | Context building + LLM answer generation |
| `router.py` | FastAPI endpoint definitions + Pydantic models |
| `main.py` | App factory, CORS, router registration |

---

## Deployment

All services run via Docker Compose:

```
neo4j (5.15-community)  →  port 7474 (browser), 7687 (bolt)
backend (FastAPI)        →  port 8000
frontend (Vite + React)  →  port 5173 (dev) / 80 (prod via nginx)
```

One-time setup:
1. `docker compose up neo4j -d`
2. `cd backend && poetry run python src/library/graph/schema.py` (create indexes)
3. `bash data/download.sh` (fetch PwC data)
4. `cd backend && poetry run python src/library/graph/ingest.py` (embed + load ~30 min)
5. `docker compose up --build` (start all services)
