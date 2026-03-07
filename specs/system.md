# System Spec — graphrag-neo4j

Overall conventions that apply across the entire project.

---

## Project Layout

Root is minimal — only infrastructure files. Each service is fully independent.

```
graphrag-neo4j/                  # Repo root
├── Makefile                     # Project commands (make help)
├── env.example                  # Template for root-level secrets
├── .env                         # NOT committed — copy from env.example
├── .gitignore
├── README.md
├── docker/                      # Docker Compose files
│   ├── docker-compose.dev.yml   # Development stack (Neo4j + backend + frontend)
│   └── docker-compose.run.yml   # Production stack (optional)
└── data/                        # PwC data — mounted into backend container
    ├── download.sh
    ├── papers.json
    ├── methods.json
    ├── tasks.json
    ├── datasets.json
    └── evaluations.json

backend/                         # Independent Python service
├── pyproject.toml               # Poetry: deps + tool config
├── poetry.toml                  # Poetry local config (in-project venv)
├── poetry.lock
├── Dockerfile
│
├── src/                         # Python source root
│   └── graphrag_service/        # ← Main package (Poetry: packages = [{include = "graphrag_service", from = "src"}])
│       ├── __init__.py
│       ├── main.py              # FastAPI app factory (create_app)
│       ├── router.py            # Aggregates module routers under /api/v1/
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Pydantic Settings (get_settings with lru_cache)
│       │   ├── auth.py          # X-API-Key dependency
│       │   ├── logging.py       # structlog setup
│       │   └── dependencies.py  # FastAPI deps (Neo4j client lifecycle)
│       ├── dbase/               # Database layer
│       │   ├── __init__.py
│       │   └── neo4j/
│       │       ├── __init__.py
│       │       ├── client.py    # Neo4j client via neomodel
│       │       └── models/
│       │           ├── __init__.py      # Re-exports all models (neomodel registry)
│       │           ├── base.py          # Abstract BaseNode (uid + created_at)
│       │           ├── nodes.py         # Paper, Method, Task, Dataset
│       │           └── relationships.py # UsedForRel, EvaluatedOnRel
│       ├── library/             # Reusable logic (can use frameworks, not tied to modules/DB)
│       │   ├── __init__.py
│       │   ├── parsers.py       # JSON data parsing (iter_papers, iter_methods, etc.)
│       │   ├── generator.py     # Context formatting and prompt building
│       │   ├── llm/             # LangChain-based LLM abstraction (provider-agnostic)
│       │   │   ├── __init__.py  # Re-exports: get_chat_model, get_embeddings, generate, embed_*
│       │   │   ├── providers.py # Provider factory (OpenAI, Gemini, Ollama, Qwen)
│       │   │   ├── chat.py      # Chat model wrapper (generate with prompt)
│       │   │   └── embeddings.py # Embedding wrapper (embed_text, embed_batch)
│       │   └── graph/           # LangGraph workflow definitions
│       │       ├── __init__.py  # Re-exports: run_rag_pipeline
│       │       └── rag_pipeline.py # RAG pipeline as LangGraph StateGraph
│       ├── shared/              # Cross-module shared concerns
│       │   ├── __init__.py
│       │   ├── exceptions.py    # Exception hierarchy
│       │   ├── utils/
│       │   │   └── __init__.py
│       │   ├── services/        # Shared services (used by multiple modules)
│       │   │   └── __init__.py
│       │   └── repositories/    # Shared repositories (used by multiple modules)
│       │       └── __init__.py
│       ├── modules/             # Feature modules (Handler → UseCase → Service → Repo)
│       │   ├── __init__.py
│       │   ├── health/          # Health check module
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── services.py
│       │   │   ├── usecase.py
│       │   │   ├── apiv1/
│       │   │   │   ├── __init__.py
│       │   │   │   └── handler.py
│       │   │   └── cli/
│       │   │       ├── __init__.py
│       │   │       └── commands.py
│       │   ├── graph/           # Graph schema, parsing, ingestion, exploration
│       │   │   ├── __init__.py
│       │   │   ├── schemas.py
│       │   │   ├── services.py      # Orchestrates library calls (parsing, embedding)
│       │   │   ├── repositories.py  # DB operations (schema install, node upsert, explore)
│       │   │   ├── usecase.py       # Orchestrates service + repository
│       │   │   ├── apiv1/
│       │   │   │   ├── __init__.py
│       │   │   │   └── handler.py
│       │   │   └── cli/
│       │   │       ├── __init__.py
│       │   │       └── commands.py  # graph schema, graph ingest, graph status
│       │   └── rag/             # RAG pipeline: embed, retrieve, generate
│       │       ├── __init__.py
│       │       ├── schemas.py
│       │       ├── services.py      # Orchestrates library calls (embed, generate)
│       │       ├── repositories.py  # DB operations (vector search, traversal)
│       │       ├── usecase.py       # Orchestrates service + repository
│       │       └── apiv1/
│       │           ├── __init__.py
│       │           └── handler.py
│       └── cli/                 # Typer-based CLI
│           ├── __init__.py
│           ├── base.py          # Rich console setup
│           └── main.py          # CLI entry point, registers module commands
│
└── tests/                       # All Python tests — inside backend/
    ├── conftest.py
    ├── unit/
    │   ├── conftest.py
    │   ├── modules/
    │   │   ├── graph/
    │   │   └── rag/
    │   ├── core/
    │   └── dbase/neo4j/
    ├── integration/
    │   └── modules/graph/
    └── e2e/
        └── {feature}/
            ├── mock/
            └── bdd/
                └── features/

frontend/                        # Independent React app
├── package.json
├── package-lock.json
├── Dockerfile
├── .env                         # VITE_* vars (NOT committed)
├── .env.example
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── components/
    │   ├── ui/
    │   ├── ChatPanel.tsx
    │   ├── GraphViewer.tsx
    │   └── CypherPanel.tsx
    ├── lib/api.ts
    └── types/api.ts
```

---

## Environment Variables

**Two env files — root `.env` serves both Docker and backend.**

| File | Where | Purpose | Committed? |
|------|-------|---------|-----------|
| `env.example` | repo root | Template with placeholder values | Yes |
| `.env` | repo root | Secrets for local dev + Docker Compose | No |
| `frontend/.env` | `frontend/` | Frontend vars (`VITE_*`) | No |
| `frontend/.env.example` | `frontend/` | Template for frontend vars | Yes |

### Root `env.example` → copy to `.env`

Used by Docker Compose (`env_file: ../.env`) and by the backend running locally.

```bash
# .env  (copy from env.example, fill in values)

# Application
APP_NAME="GraphRAG Service"
APP_VERSION="0.1.0"
APP_ENVIRONMENT="development"
APP_HOST="0.0.0.0"
APP_PORT=8005
APP_DEBUG=true

# API Authentication
APP_X_API_KEY="changeme-in-production"

# CORS
ALLOWED_ORIGINS_STR="http://localhost:3000,http://localhost:5173"

# Neo4j
NEO4J_URI=bolt://localhost:7687       # Docker: bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM (provider-agnostic via LangChain)
LLM_PROVIDER=openai            # openai | google | ollama | qwen
LLM_MODEL=gpt-4o-mini

# Embeddings (provider-agnostic via LangChain)
EMBEDDING_PROVIDER=openai      # openai | google | ollama | qwen
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Provider API Keys (set only the ones you use)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Ollama (local models)
OLLAMA_BASE_URL=http://localhost:11434

# RAG
TOP_K_SEED_NODES=5
TRAVERSAL_DEPTH=2

# Data
DATA_DIR=data
MAX_PAPERS=5000
INGEST_BATCH_SIZE=50
```

### `frontend/.env`

Only Vite-prefixed vars. These are embedded into the JS bundle at build time.

```bash
# frontend/.env
VITE_API_URL=http://localhost:8005
VITE_API_KEY=changeme-in-production     # Same value as APP_X_API_KEY
```

Access in code: `import.meta.env.VITE_API_URL`
**NOT** `process.env.*` — this is Vite, not Node/Next.js.

### `graphrag_service/core/config.py`

```python
from functools import lru_cache
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    APP_NAME: str = Field(default="GraphRAG Service")
    APP_PORT: int = Field(default=8005)
    APP_ENVIRONMENT: str = Field(default="development")
    APP_DEBUG: bool = Field(default=False)
    APP_X_API_KEY: str = Field(default="changeme")
    ALLOWED_ORIGINS_STR: str = Field(default="http://localhost:3000,http://localhost:5173")

    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password123")

    # LLM
    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL: str = Field(default="gpt-4o-mini")

    # Embeddings
    EMBEDDING_PROVIDER: str = Field(default="openai")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIM: int = Field(default=1536)

    # Provider API Keys
    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")

    TOP_K_SEED_NODES: int = Field(default=5)
    TRAVERSAL_DEPTH: int = Field(default=2)

    DATA_DIR: str = Field(default="data")
    MAX_PAPERS: int = Field(default=5000)
    INGEST_BATCH_SIZE: int = Field(default=50)

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS_STR.split(",")]

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**Rule**: Import `get_settings` from `graphrag_service.core.config` everywhere. Never use `os.environ` directly.

---

## Docker Compose

Docker files live in `docker/`. Services reference parent context paths.

```yaml
# docker/docker-compose.dev.yml
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: graph-rag-neo4j
    ports:
      - "7474:7474"         # Neo4j Browser
      - "7687:7687"         # Bolt
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - graphrag-network

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: graph-rag-backend
    ports:
      - "8005:8005"
    env_file:
      - ../.env
    environment:
      NEO4J_URI: bolt://neo4j:7687
    volumes:
      - ../backend/src:/app/src
      - ../data:/app/data
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - graphrag-network

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    container_name: graph-rag-frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8005
    depends_on:
      - backend
    networks:
      - graphrag-network

networks:
  graphrag-network:
    driver: bridge

volumes:
  neo4j_data:
```

**`backend/Dockerfile` — key lines:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && poetry install --only main --no-root --no-cache
COPY . .
EXPOSE 8005
CMD ["poetry", "run", "start"]
```

**Setup and daily commands via Makefile (run from repo root):**

```bash
# First-time setup
make setup              # Creates .env + installs deps
make neo4j              # Start Neo4j container
make schema             # Create constraints + vector indexes (via CLI)
make download           # Download PwC JSON data
make ingest             # Ingest data into Neo4j (~30 min)

# Daily development
make backend            # FastAPI dev server on port 8005
make frontend           # Vite dev server on port 5173
make dev                # Both in parallel

# Docker (full stack)
make docker-up          # Start all services
make docker-build       # Build and start all services
make docker-down        # Stop all services

# CLI commands
make cli-schema         # poetry run cli graph schema
make cli-ingest         # poetry run cli graph ingest
make cli-status         # poetry run cli graph status
```

---

## Shared Patterns

### Error Handling

All Python functions must raise typed exceptions from `shared/exceptions.py`.

```python
# Exception hierarchy
BaseServiceException
├── ValidationException
├── RepositoryException
│   └── Neo4jConnectionException
├── ServiceException
│   └── OpenAIException
└── BaseHTTPException (extends FastAPI HTTPException)
```

```python
# Good
try:
    result = client.run_query(cypher, params)
except Exception as e:
    raise RepositoryException(f"Query failed: {e}")

# Bad — never do this
try:
    result = client.run_query(cypher, params)
except:
    return None
```

### Logging

Uses **structlog** configured in `core/logging.py`. Get logger via `get_logger(__name__)`.

```python
from graphrag_service.core.logging import get_logger
logger = get_logger(__name__)

# Structured context via keyword args
logger.info("Batch embedded", batch=i, total=total_batches, size=len(batch))
logger.error("Query failed", cypher=cypher[:100], error=str(e))
```

### Immutability

Always return new objects, never mutate in place:

```python
# Good
def clean_paper(raw: dict) -> dict:
    return {
        "uid": raw.get("paper_url", raw.get("id", "")),
        "title": raw["title"].strip(),
        "abstract": raw.get("abstract", ""),
    }

# Bad — mutates input
def clean_paper(raw: dict) -> dict:
    raw["uid"] = raw["paper_url"]
    return raw
```

### Type Hints

All functions require type hints. No exceptions.

```python
# Good
def embed_text(text: str) -> list[float]:
    ...

def run_query(cypher: str, params: dict | None = None) -> list:
    ...

# Bad
def embed_text(text):
    ...
```

### File Size Limits

- Max 400 lines per file
- Max 50 lines per function
- If a file grows beyond 400 lines, split by responsibility

---

## Testing

Tests live **inside each service** — not at repo root.

| Service | Test dir | Runner | Coverage |
|---------|---------|--------|---------|
| Backend | `backend/tests/` | `poetry run pytest` | >= 80% |
| Frontend | `frontend/src/` (co-located or `__tests__/`) | `npm run test` | >= 80% |

```bash
# Backend tests (from repo root via Makefile)
make test                  # All tests
make test-unit             # Unit tests only
make test-integration      # Integration tests (requires Neo4j)
make test-coverage         # Tests with coverage report

# Or from backend/
cd backend
poetry run pytest tests/ -v
poetry run pytest tests/ --cov=graphrag_service --cov-report=term-missing --cov-fail-under=80
```

Test file mirrors source file (from `graphrag_service/` perspective):
```
backend/src/graphrag_service/modules/rag/services.py   ↔  backend/tests/unit/modules/rag/test_services.py
backend/src/graphrag_service/modules/graph/services.py ↔  backend/tests/unit/modules/graph/test_services.py
backend/src/graphrag_service/dbase/neo4j/client.py     ↔  backend/tests/unit/dbase/neo4j/test_client.py
```

Note: `--cov=graphrag_service` measures coverage of the package.

---

## Code Style

### Python (`backend/pyproject.toml`)

```toml
[tool.poetry]
name = "graphrag-service"
version = "0.1.0"
packages = [{include = "graphrag_service", from = "src"}]

[tool.poetry.scripts]
start = "graphrag_service.main:main"
dev = "graphrag_service.main:dev"
cli = "graphrag_service.cli.main:main"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.29"}
pydantic = "^2.7"
pydantic-settings = "^2.2"
neo4j = "^6.1"
neomodel = "^6.1"
langchain-core = "^0.3"
langgraph = "^0.3"
langchain-openai = "^0.3"
structlog = "^24.1"
typer = {extras = ["all"], version = "^0.12"}
rich = "^13.7"
tqdm = "^4.66"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.isort]
profile = "black"
known_first_party = ["graphrag_service"]
```

**`pythonpath = ["src"]`** means pytest resolves imports from `src/`:
```python
from graphrag_service.core.config import get_settings  # resolves → src/graphrag_service/core/config.py
from graphrag_service.modules.rag.services import RAGService  # resolves → src/graphrag_service/modules/rag/services.py
```

- **Formatter**: `poetry run black src/ tests/`
- **Linter**: `poetry run isort src/ tests/`
- **Type checker**: `poetry run mypy src/`

### TypeScript / React (`frontend/package.json` scripts)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "lint": "eslint src --ext ts,tsx",
    "format": "prettier --write src"
  }
}
```

---

## Git Commit Format

```
<type>: <description>

Types: feat, fix, refactor, docs, test, chore, perf
```

Examples:
```
feat: add vector search with neomodel VectorFilter
fix: handle empty abstract in paper parser
test: add embedder batch size boundary tests
chore: update docker compose neo4j to 5.15
```
