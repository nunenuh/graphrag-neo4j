# GraphRAG Service — Backend

FastAPI backend for the GraphRAG system. Provides graph exploration, RAG query answering, and data ingestion via API and CLI.

## Architecture

```
Handler (API/CLI) → UseCase → Service (library calls) → Repository (DB queries)
```

Each module follows this layering pattern. The `library/` package contains reusable logic (LLM, parsers, pipeline) that is framework-aware but not tied to specific modules.

## Package Structure

```
src/graphrag_service/
├── main.py                 # FastAPI app factory
├── router.py               # Aggregates module routers under /api/v1/
├── core/                   # Config, auth, dependencies, logging
├── dbase/neo4j/            # Neo4j client (neomodel) + OGM models
│   └── models/             # Paper, Method, Task, Dataset, relationships
├── library/                # Reusable logic
│   ├── parsers.py          # PwC JSON parsing
│   ├── generator.py        # Context builder for LLM
│   ├── llm/                # LangChain abstraction (4 providers)
│   │   ├── chat.py         # generate()
│   │   ├── embeddings.py   # embed_text(), embed_batch()
│   │   └── providers/      # openai, google, ollama, qwen
│   └── graph/              # LangGraph pipelines
│       └── rag_pipeline.py # RAG as StateGraph (embed→search→traverse→context→generate)
├── modules/
│   ├── health/             # GET /ping, GET /status
│   ├── graph/              # GET /schema, /explore, /stats, /nodes/{uid}, /search
│   └── rag/                # POST /query
├── shared/                 # Exceptions, utilities
└── cli/                    # Typer CLI (graph schema, graph ingest, graph status)
```

## Setup

```bash
# From repo root
make install-backend       # poetry install --with dev

# Or manually
cd backend
poetry install --with dev
```

## Running

```bash
# Dev server (auto-reload)
make backend               # from repo root
# or
cd backend && poetry run dev

# Production
cd backend && poetry run start
```

Default port: **8005**

## Testing

```bash
make test-unit             # unit tests
make test-coverage         # with coverage report

# Or manually
cd backend
poetry run pytest tests/unit/ -v
poetry run pytest tests/ --cov=graphrag_service --cov-report=term-missing
```

Current: **143 tests, 74% coverage**. See [specs/backend/test-gaps.md](../specs/backend/test-gaps.md) for edge case gap analysis.

## CLI

```bash
cd backend
poetry run cli graph schema     # create Neo4j constraints + vector indexes
poetry run cli graph ingest     # ingest PwC data (~30 min)
poetry run cli graph status     # show node/edge counts
poetry run cli health check     # test Neo4j connectivity
poetry run cli --help           # all commands
```

## Configuration

All settings via environment variables (see [env.example](../env.example)). Loaded by Pydantic Settings in `core/config.py`.

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | 8005 | Server port |
| `APP_X_API_KEY` | changeme | API key for auth |
| `NEO4J_URI` | bolt://localhost:7687 | Neo4j connection |
| `LLM_PROVIDER` | openai | LLM provider (openai/google/ollama/qwen) |
| `EMBEDDING_PROVIDER` | openai | Embedding provider |
| `EMBEDDING_DIM` | 1536 | Embedding vector dimension |
| `TOP_K_SEED_NODES` | 5 | Vector search top-k |
| `INGEST_BATCH_SIZE` | 50 | Nodes per ingestion batch |

## Graph Schema (Neo4j)

**Nodes**: Paper, Method, Task, Dataset (all with vector embeddings)

**Relationships**: `USED_FOR` (Dataset→Task), `EVALUATED_ON` (Method→Dataset)

See [specs/backend/neo4j-models.md](../specs/backend/neo4j-models.md) for full model definitions.

## Dependencies

- **FastAPI** + Uvicorn — API framework
- **neomodel** — Neo4j OGM (models, vector indexes, queries)
- **LangChain** — provider-agnostic LLM/embedding abstraction
- **LangGraph** — RAG pipeline as stateful graph
- **Pydantic** — settings, request/response validation
- **structlog** — structured logging
- **Typer** + Rich — CLI framework
