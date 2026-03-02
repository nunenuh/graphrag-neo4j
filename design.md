# Graph RAG with Neo4j — Design Document

**Date:** 2026-03-02
**Status:** Approved
**Type:** Portfolio Project

---

## 1. Overview

A full-stack **Graph Retrieval-Augmented Generation (Graph RAG)** system using Neo4j as the unified graph + vector store. Users ask natural language questions about the ML research landscape — the system retrieves structured relational context from a knowledge graph and generates grounded answers.

**Why Graph RAG over traditional RAG:**
- Traditional RAG retrieves similar *text chunks* — no awareness of relationships
- Graph RAG retrieves a *subgraph* — structured relationships between entities
- Multi-hop reasoning: "What datasets are used by methods that solve tasks related to YOLO?" — impossible with vector search alone, trivial with graph traversal

---

## 2. Goals

- Demonstrate deep understanding of Graph RAG (not just calling a library)
- Showcase Neo4j's native vector index alongside graph traversal in one query
- Build an impressive, self-contained portfolio project with a real UI
- Use freely available, recognizable data (Papers With Code)

---

## 3. Tech Stack

| Layer               | Technology                                       | Reason                                                        |
| ------------------- | ------------------------------------------------ | ------------------------------------------------------------- |
| Graph + Vector DB   | Neo4j 5.11+                                      | Native vector index + Cypher traversal in one DB              |
| Embeddings          | OpenAI `text-embedding-3-small`                  | 1536-dim, fast, cheap                                         |
| LLM                 | OpenAI GPT-4o-mini                               | Cost-efficient, strong reasoning                              |
| Backend             | FastAPI (Python)                                 | Async, clean, pythonic                                        |
| Frontend            | Vite + React + TypeScript + Tailwind + shadcn/ui | SPA-first, no SSR overhead, compatible with canvas graph libs |
| Graph Visualization | react-force-graph                                | Interactive node/edge rendering                               |
| Infra               | Docker Compose                                   | One command setup                                             |
| Data                | Papers With Code JSON dumps                      | Free, structured, ML-domain                                   |

---

## 4. Data & Graph Schema

### Source
Papers With Code provides free JSON dumps:
- `papers.json` — titles, abstracts, arXiv IDs, years
- `methods.json` — algorithm names, descriptions
- `tasks.json` — ML task taxonomy (NLP, CV, RL, etc.)
- `datasets.json` — benchmark datasets
- `evaluations.json` — method + dataset + metric + score (pre-built edges)

### Neo4j Node Schema

```cypher
(:Paper    {id, title, abstract, year, url, embedding: float[1536]})
(:Method   {id, name, full_name, description, embedding: float[1536]})
(:Task     {id, name, area, description, embedding: float[1536]})
(:Dataset  {id, name, description, modalities, embedding: float[1536]})
```

### Neo4j Relationship Schema

```cypher
(:Paper)   -[:INTRODUCES]->                   (:Method)
(:Paper)   -[:ADDRESSES]->                    (:Task)
(:Method)  -[:APPLIED_ON]->                   (:Dataset)
(:Method)  -[:EVALUATED_ON {metric, score}]-> (:Dataset)
(:Dataset) -[:USED_FOR]->                     (:Task)
(:Method)  -[:VARIANT_OF]->                   (:Method)
(:Task)    -[:SUBTASK_OF]->                   (:Task)
```

### Vector Indexes (one per node type)

```cypher
CREATE VECTOR INDEX paper_embeddings   FOR (p:Paper)    ON (p.embedding)
CREATE VECTOR INDEX method_embeddings  FOR (m:Method)   ON (m.embedding)
CREATE VECTOR INDEX task_embeddings    FOR (t:Task)     ON (t.embedding)
CREATE VECTOR INDEX dataset_embeddings FOR (d:Dataset)  ON (d.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}}
```

---

## 5. RAG Pipeline

### Phase 1 — Ingest

```
Papers With Code JSON
        │
        ▼
Parse + clean entities (papers, methods, tasks, datasets)
        │
        ▼
Generate embeddings (OpenAI text-embedding-3-small)
        │
        ▼
Load nodes + properties + embeddings into Neo4j
        │
        ▼
Create relationships from evaluations.json
        │
        ▼
Create vector indexes
```

### Phase 2 — Query (Hybrid Graph RAG)

```
User Question (natural language)
        │
        ▼
[OpenAI] Embed question → 1536-dim query vector
        │
        ▼
[Neo4j Vector Index] Similarity search across all node types
  → Returns top-k seed nodes with similarity scores
  → e.g. (:Task "Object Detection"), (:Method "YOLO")
        │
        ▼
[Neo4j Graph Traversal] Walk edges from seed nodes (depth 1–2)
  MATCH (seed)-[:INTRODUCES|APPLIED_ON|EVALUATED_ON|USED_FOR*1..2]->(related)
  → Collect surrounding subgraph (nodes + relationships)
        │
        ▼
[Context Builder] Serialize subgraph as structured text
  → "YOLO -[APPLIED_ON]-> COCO Dataset
      COCO -[USED_FOR]-> Object Detection Task
      YOLO -[EVALUATED_ON {mAP: 45.5}]-> COCO"
        │
        ▼
[OpenAI GPT-4o-mini] Generate grounded answer from subgraph context
        │
        ▼
Return: {answer, seed_nodes, subgraph, cypher_used, scores}
```

### The Killer Query (vector + graph in one Cypher)

```cypher
CALL db.index.vector.queryNodes('method_embeddings', 5, $queryVector)
YIELD node AS method, score
MATCH (method)-[:APPLIED_ON]->(dataset)
MATCH (method)<-[:INTRODUCES]-(paper)
MATCH (dataset)-[:USED_FOR]->(task)
RETURN
  method.name,
  method.description,
  collect(DISTINCT dataset.name) AS datasets,
  collect(DISTINCT paper.title)  AS papers,
  collect(DISTINCT task.name)    AS tasks,
  score
ORDER BY score DESC
```

---

## 6. FastAPI Backend

### Project Structure

```
backend/
├── pyproject.toml           # Poetry: deps + tool config (pythonpath = ["src"])
├── Dockerfile
└── src/                     # ← Python path root — all imports start from here
    ├── main.py              # FastAPI app factory, CORS, router registration
    ├── router.py            # All endpoint definitions + Pydantic models
    ├── core/
    │   ├── config.py        # Pydantic Settings (env vars)
    │   └── security.py      # X-API-Key dependency
    ├── dbase/
    │   └── neo4j/
    │       └── client.py    # Neo4j driver wrapper (run_query)
    ├── library/
    │   ├── graph/
    │   │   ├── schema.py    # CREATE CONSTRAINT / CREATE INDEX
    │   │   ├── parser.py    # PwC JSON → clean entity dicts
    │   │   └── ingest.py    # Orchestrate: parse → embed → load
    │   └── rag/
    │       ├── embedder.py  # OpenAI embedding (single + batch)
    │       ├── retriever.py # Vector search → graph traversal
    │       └── generator.py # Context build + LLM answer
    └── modules/             # Feature modules (optional, for future expansion)
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/query` | Main RAG pipeline — question → answer + subgraph |
| `GET` | `/api/graph/schema` | Returns node/edge type definitions |
| `GET` | `/api/graph/explore` | Returns sample graph data for visualization |
| `GET` | `/api/graph/node/{id}` | Returns single node + its neighbors |
| `GET` | `/api/health` | Health check |

### Query Response Shape

```json
{
  "answer": "YOLO is evaluated on COCO (45.5 mAP) and Pascal VOC...",
  "seed_nodes": [
    {"id": "yolo", "type": "Method", "name": "YOLO", "score": 0.92}
  ],
  "subgraph": {
    "nodes": [...],
    "edges": [{"from_id": "yolo", "to_id": "coco", "type": "APPLIED_ON"}]
  },
  "cypher_used": "CALL db.index.vector.queryNodes(...) ...",
  "latency_ms": 340
}
```

---

## 7. React Frontend (Vite + shadcn/ui)

### Layout (3-panel)

```
┌─────────────────────────────────────────────────────┐
│  🧠 Graph RAG Explorer — ML Knowledge Graph         │
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│  💬 Chat Panel       │  🕸️ Graph Visualization      │
│                      │                              │
│  Q: "What datasets   │  [Interactive force graph]   │
│  are used for NLP?"  │  Nodes: Paper/Method/Task    │
│                      │  Edges: highlighted path     │
│  A: "GLUE, SQuAD,   │  Seed nodes: orange          │
│  and CoNLL are the   │  Traversed nodes: blue       │
│  most common..."     │                              │
│                      │                              │
├──────────────────────┴──────────────────────────────┤
│  🔧 Cypher Query Used (expandable)                  │
└─────────────────────────────────────────────────────┘
```

### Component Structure

```
frontend/
├── src/
│   ├── App.tsx              # Main layout (2-panel)
│   ├── main.tsx             # Vite entry point
│   ├── components/
│   │   ├── ChatPanel.tsx    # Q&A chat (shadcn Input, Button, Badge, ScrollArea)
│   │   ├── GraphViewer.tsx  # react-force-graph-2d visualization
│   │   ├── CypherPanel.tsx  # Cypher query (shadcn Collapsible)
│   │   └── ui/              # shadcn components (auto-generated)
│   └── lib/
│       ├── api.ts           # FastAPI client (import.meta.env.VITE_API_URL)
│       └── types.ts         # Shared TypeScript types
├── .env.local               # VITE_API_URL=http://localhost:8000
└── package.json
```

---

## 8. Infrastructure

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5.15-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [neo4j]
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

---

## 9. What Makes This Stand Out

| Feature | Why It Impresses |
|---------|-----------------|
| Neo4j as unified graph + vector store | One DB does both — no Pinecone/Chroma |
| Vector search + graph traversal in one Cypher | Deep Neo4j knowledge |
| Subgraph returned and visualized | Explainable AI — user sees *why* |
| Cypher shown in UI | Transparent, not a black box |
| Papers With Code domain | Legible to any ML engineer |
| Docker Compose one-command setup | Reviewer can run it in minutes |

---

## 10. Out of Scope (v1)

- Authentication / user sessions
- Persistent chat history
- Fine-tuned LLM
- Real-time streaming responses
- Full Papers With Code dataset (use curated subset ~5k papers)
