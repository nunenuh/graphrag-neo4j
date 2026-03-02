# System Spec — graphrag-neo4j

Overall conventions that apply across the entire project.

---

## Project Layout

Root is minimal — only infrastructure files. Each service is fully independent.

```
graphrag-neo4j/                  # Repo root
├── docker-compose.yml
├── .env.example                 # Template for backend secrets
├── .gitignore
├── README.md
└── data/                        # PwC data — mounted into backend container
    ├── download.sh
    ├── papers.json
    ├── methods.json
    ├── tasks.json
    ├── datasets.json
    └── evaluations.json

backend/                         # Independent Python service
├── pyproject.toml               # Poetry: deps + tool config (pythonpath = ["src"])
├── poetry.lock
├── Dockerfile
├── .env                         # NOT committed — copy from root .env.example
│
├── src/                         # ← All Python source (Python path root)
│   ├── main.py                  # FastAPI app factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── dbase/                   # Database layer
│   │   ├── __init__.py
│   │   └── neo4j/
│   │       ├── __init__.py
│   │       └── client.py        # Neo4j driver wrapper
│   ├── library/                 # Reusable internal libraries
│   │   ├── __init__.py
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── schema.py
│   │   │   ├── parser.py
│   │   │   └── ingest.py
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── embedder.py
│   │       ├── retriever.py
│   │       └── generator.py
│   ├── router.py                # Main API router — endpoint definitions + Pydantic models
│   └── modules/                 # Feature modules (Handler → UseCase → Service → Repo)
│       └── {module_name}/       # e.g. papers/, methods/, tasks/
│           ├── __init__.py
│           ├── apiv1/
│           │   ├── __init__.py
│           │   └── handler.py
│           ├── schemas.py
│           ├── usecase.py
│           ├── services.py      # When business logic needed
│           └── repositories.py  # When DB access needed
│
└── tests/                       # All Python tests — inside backend/
    ├── conftest.py
    ├── unit/                    # Mirrors src/ — mocked deps
    │   ├── library/rag/
    │   ├── library/graph/
    │   ├── core/
    │   └── dbase/neo4j/
    ├── integration/             # Mirrors src/ — real Neo4j test DB
    │   └── library/graph/
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
├── .env.example                 # Template (committed)
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

**Three separate env files — never mix them.**

| File | Where | Purpose | Committed? |
|------|-------|---------|-----------|
| `.env.example` | repo root | Template with placeholder values | ✅ Yes |
| `backend/.env` | `backend/` | Secrets for local dev (Neo4j, OpenAI, API_KEY) | ❌ No |
| `frontend/.env` | `frontend/` | Frontend vars (`VITE_*`) | ❌ No |
| `frontend/.env.example` | `frontend/` | Template for frontend vars | ✅ Yes |

### Root `.env.example` → copy to `backend/.env`

Used by Docker Compose (`env_file: ./backend/.env`) and by the backend running locally.

```bash
# backend/.env  (copy from root .env.example, fill in values)

# Neo4j
NEO4J_URI=bolt://neo4j:7687        # Docker: use service name "neo4j"
NEO4J_USER=neo4j                   # Local: use bolt://localhost:7687
NEO4J_PASSWORD=your-password-here

# OpenAI
OPENAI_API_KEY=sk-...

# Security
API_KEY=your-api-key-here          # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY_ENABLED=true

# App
APP_ENV=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173
```

### `frontend/.env`

Only Vite-prefixed vars. These are embedded into the JS bundle at build time.

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your-api-key-here     # Same value as backend API_KEY
```

Access in code: `import.meta.env.VITE_API_URL`
**NOT** `process.env.*` — this is Vite, not Node/Next.js.

### `backend/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    openai_api_key: str
    api_key: str = ""
    api_key_enabled: bool = True
    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"   # Reads backend/.env when running from backend/

settings = Settings()
```

**Rule**: Import `settings` from `core.config` everywhere. Never use `os.environ` directly.

---

## Docker Compose

Each service builds from its own directory. Env vars for backend come from `backend/.env`.

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"         # Neo4j Browser
      - "7687:7687"         # Bolt
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data

  backend:
    build: ./backend        # Uses backend/Dockerfile
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    volumes:
      - ./data:/app/data    # Mount PwC JSON into container
    depends_on:
      - neo4j

  frontend:
    build: ./frontend       # Uses frontend/Dockerfile
    ports:
      - "5173:5173"         # dev
      # - "80:80"           # prod (nginx)
    depends_on:
      - backend

volumes:
  neo4j_data:
```

**`backend/Dockerfile` — key lines:**
```dockerfile
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-root
COPY src/ ./src/
COPY . .
ENV PYTHONPATH=/app/src          # Makes imports work without prefix inside container
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**One-time setup (run from repo root):**

```bash
# 1. Start Neo4j
docker compose up neo4j -d

# 2. Create Neo4j schema (run from backend/)
cd backend && poetry run python src/library/graph/schema.py

# 3. Download PwC data (run from repo root)
bash data/download.sh

# 4. Ingest data (~30 min, run from backend/)
cd backend && poetry run python src/library/graph/ingest.py
```

**Start everything:**
```bash
docker compose up --build
```

---

## Shared Patterns

### Error Handling

All Python functions must raise typed exceptions. Never swallow errors silently.

```python
# Good
try:
    result = neo4j_client.run_query(cypher, params)
except Exception as e:
    logger.error(f"Query failed: {e}")
    raise HTTPException(status_code=500, detail="Graph query failed")

# Bad — never do this
try:
    result = neo4j_client.run_query(cypher, params)
except:
    return None
```

### Logging

Use Python's `logging` module. Configure via `LOG_LEVEL` env var.

```python
import logging
logger = logging.getLogger(__name__)

# Use structured messages
logger.info("Embedding batch", extra={"batch_size": len(texts), "total": total})
logger.error("OpenAI call failed", extra={"error": str(e)})
```

### Immutability

Always return new objects, never mutate in place:

```python
# Good
def clean_paper(raw: dict) -> dict:
    return {
        "id": raw["paper_url"].split("/")[-1],
        "title": raw["title"].strip(),
        "abstract": raw.get("abstract", ""),
    }

# Bad — mutates input
def clean_paper(raw: dict) -> dict:
    raw["id"] = raw["paper_url"].split("/")[-1]
    return raw
```

### Type Hints

All functions require type hints. No exceptions.

```python
# Good
def embed_text(text: str) -> list[float]:
    ...

def run_query(cypher: str, params: dict) -> list[dict]:
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
| Backend | `backend/tests/` | `poetry run pytest` | ≥80% |
| Frontend | `frontend/src/` (co-located or `__tests__/`) | `npm run test` | ≥80% |

```bash
# Backend tests (from backend/)
cd backend
poetry run pytest tests/ -v
poetry run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80

# By layer
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v           # Requires Neo4j running
poetry run pytest tests/e2e/ -k "mock" -v         # Fast, no services needed
poetry run pytest tests/e2e/ -k "bdd" -v          # Requires full stack running

# Frontend tests (from frontend/)
cd frontend
npm run test       # vitest
npm run test:ui    # vitest with browser UI
```

Test file mirrors source file (from `src/` perspective):
```
backend/src/library/rag/embedder.py   ↔  backend/tests/unit/library/rag/test_embedder.py
backend/src/library/graph/parser.py  ↔  backend/tests/unit/library/graph/test_parser.py
backend/src/dbase/neo4j/client.py     ↔  backend/tests/unit/dbase/neo4j/test_client.py
backend/src/router.py                 ↔  backend/tests/e2e/query/mock/test_query_mock.py
```

Note: `--cov=src` measures coverage of `src/` directory (not `tests/`).

---

## Code Style

### Python (`backend/pyproject.toml`)

```toml
[tool.poetry]
name = "graphrag-neo4j-backend"
version = "0.1.0"
description = "Graph RAG over ML research papers"
python = "^3.11"
packages = [{include = "src"}]       # Tells Poetry the source root

[tool.poetry.dependencies]
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
neo4j = "^5.15"
openai = "^1.40"
pydantic-settings = "^2.4"

[tool.poetry.group.dev.dependencies]
black = "^24.0"
ruff = "^0.4"
mypy = "^1.10"

[tool.poetry.group.test.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
pytest-bdd = "^7.0"
pytest-mock = "^3.12"
httpx = "^0.27"
factory-boy = "^3.3"

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]                 # Adds src/ to Python path — imports work without prefix
```

**`pythonpath = ["src"]`** means pytest (and uvicorn when run from `backend/`) resolves imports from `src/`:
```python
from core.config import settings    # resolves → backend/src/core/config.py
from library.rag.embedder import embed_text # resolves → backend/src/library/rag/embedder.py
```

- **Formatter**: `poetry run black src/ tests/`
- **Linter**: `poetry run ruff check src/ tests/`
- **Type checker**: `poetry run mypy src/`

### TypeScript / React (`frontend/package.json` scripts)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "lint": "eslint src --ext ts,tsx",
    "format": "prettier --write src"
  }
}
```

- **Formatter**: `prettier` — `npm run format`
- **Linter**: `eslint` with TypeScript rules — `npm run lint`
- Strict TypeScript (`"strict": true` in `tsconfig.json`)
- No `any` types — define proper interfaces

---

## Git Commit Format

```
<type>: <description>

Types: feat, fix, refactor, docs, test, chore, perf
```

Examples:
```
feat: add vector search with depth-2 graph traversal
fix: handle empty abstract in paper parser
test: add embedder batch size boundary tests
chore: update docker compose neo4j to 5.15
```
