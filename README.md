# graphrag-neo4j

Full-stack **Graph RAG** using Neo4j as a unified graph + vector store.
Ask natural language questions about the ML research landscape —
the system retrieves a knowledge subgraph and generates grounded answers.

## Why Graph RAG (not just RAG)

Traditional RAG retrieves *similar text chunks*.
This retrieves a *knowledge subgraph* — enabling multi-hop reasoning
that vector search cannot do alone.

```
Question → Embed → Vector Search → 2-hop Graph Traverse → LLM Answer
                    (seed nodes)     (subgraph context)    (grounded)
```

## Stack

| Layer | Tech |
|-------|------|
| Graph + Vector DB | Neo4j 5.15 (neomodel OGM) |
| Backend | FastAPI + Python 3.11 + LangGraph + LangChain |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui |
| LLM | Provider-agnostic: OpenAI, Google, Ollama, Qwen |
| Embeddings | Provider-agnostic (default: text-embedding-3-small) |
| Visualization | react-force-graph-2d |
| Infra | Docker Compose |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/nunenuh/graphrag-neo4j
cd graphrag-neo4j
make setup                    # creates .env, installs deps

# 2. Edit .env — set your LLM provider API key
#    OPENAI_API_KEY=sk-...  (or GOOGLE_API_KEY, QWEN_API_KEY, etc.)

# 3. Start Neo4j and load data
make neo4j                    # start Neo4j container
make schema                   # create constraints + vector indexes
make download                 # download PwC JSON data
make ingest                   # ingest into Neo4j (~30 min)

# 4. Run
make dev                      # backend (8005) + frontend (5173)
```

Open: [http://localhost:5173](http://localhost:5173) (frontend) | [http://localhost:8005/docs](http://localhost:8005/docs) (API docs)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health/ping` | Liveness check |
| `GET` | `/api/v1/health/status` | Readiness + component health |
| `GET` | `/api/v1/graph/schema` | Node labels + relationship types |
| `GET` | `/api/v1/graph/explore?limit=50` | Subgraph sample for visualization |
| `GET` | `/api/v1/graph/stats` | Node/edge counts per type |
| `GET` | `/api/v1/graph/nodes/{uid}` | Node detail with relationships |
| `GET` | `/api/v1/graph/search?q=...` | Full-text node search |
| `POST` | `/api/v1/rag/query` | RAG question answering |

All endpoints except health require `X-API-Key` header.

## Example Questions

- *"What methods are used for object detection?"*
- *"Which papers introduced transformer architectures?"*
- *"What datasets are used to benchmark image classification?"*
- *"How does BERT relate to other NLP methods?"*

## Project Structure

```
graphrag-neo4j/
├── backend/                    # FastAPI + Python service
│   ├── src/graphrag_service/   # Main package
│   │   ├── core/               # Config, auth, dependencies, logging
│   │   ├── dbase/neo4j/        # Neo4j client + neomodel models
│   │   ├── library/            # Reusable logic (LLM, parsers, pipeline)
│   │   ├── modules/            # Feature modules (graph, rag, health)
│   │   ├── shared/             # Exceptions, utilities
│   │   └── cli/                # Typer CLI commands
│   └── tests/                  # Unit / integration / e2e tests
├── frontend/                   # React + Vite app
├── docker/                     # Docker Compose files
├── data/                       # PwC data (papers, methods, tasks, datasets)
├── docs/                       # Product docs, technical docs, ADRs
├── specs/                      # Implementation specs (how to build it)
├── Makefile                    # All project commands (make help)
└── env.example                 # Environment variable template
```

## Development

```bash
make help                # show all commands
make test                # run all tests
make test-unit           # unit tests only
make test-coverage       # tests with coverage report
make lint                # syntax checks
make format              # auto-format with black + isort
make status              # check service health
```

## CLI

```bash
cd backend
poetry run cli graph schema    # create Neo4j schema
poetry run cli graph ingest    # ingest PwC data
poetry run cli graph status    # show graph statistics
poetry run cli health check    # check Neo4j connectivity
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/product/](docs/product/) | PRD, personas, user stories, MVP scope |
| [docs/technical/](docs/technical/) | Architecture, API spec, data model, ADRs |
| [specs/](specs/) | Implementation specs (backend, frontend, conventions) |
| [docs/comparison-with-full-spec.md](docs/comparison-with-full-spec.md) | Gap analysis vs full GraphRAG spec |
| [docs/backend-layout-full-spec.md](docs/backend-layout-full-spec.md) | Future backend layout for full spec |

## License

MIT
