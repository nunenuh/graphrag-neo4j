# Graph RAG with Neo4j — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack Graph RAG portfolio project using Neo4j (graph + vector), FastAPI, and Vite + React over the ML/AI knowledge domain (Papers With Code data).

**Architecture:** User questions are embedded → seed nodes found via Neo4j vector index → graph traversal expands the subgraph → LLM generates grounded answer. The frontend shows the chat answer, the traversed subgraph visually, and the raw Cypher used.

**Tech Stack:** Neo4j 5.15, Python 3.11, FastAPI, OpenAI API (embeddings + GPT-4o-mini), Vite + React + TypeScript + Tailwind + shadcn/ui, react-force-graph-2d, Docker Compose.

**Design Doc:** See [[projects/graphrag-neo4j/design]] for full schema and flow.

**Note:** The actual code repo lives at `~/projects/graphrag-neo4j/` outside the vault.

---

## Phase 1: Project Scaffold & Infrastructure

### Task 1: Create project directory structure

**Files:**
- Create: `~/projects/graphrag-neo4j/` (root)
- Create: `~/projects/graphrag-neo4j/backend/`
- Create: `~/projects/graphrag-neo4j/frontend/`
- Create: `~/projects/graphrag-neo4j/data/`

**Step 1: Initialize directory**

```bash
mkdir -p ~/projects/graphrag-neo4j/{backend,frontend,data}
cd ~/projects/graphrag-neo4j
git init
```

**Step 2: Create .gitignore**

```
.env
__pycache__/
*.pyc
.venv/
node_modules/
.next/
*.json.gz
data/*.json
```

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: initialize project structure"
```

---

### Task 2: Docker Compose with Neo4j

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Write docker-compose.yml**

```yaml
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: graph-rag-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_server_memory_heap_initial__size: 512m
      NEO4J_server_memory_heap_max__size: 1G
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: graph-rag-backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      neo4j:
        condition: service_healthy
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    container_name: graph-rag-frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  neo4j_data:
```

**Step 2: Write .env.example**

```bash
OPENAI_API_KEY=sk-...
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

**Step 3: Start Neo4j to verify**

```bash
cp .env.example .env
# Fill OPENAI_API_KEY
docker compose up neo4j -d
# Wait 15s then open: http://localhost:7474
# Login: neo4j / password123
```

Expected: Neo4j browser loads.

**Step 4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: add docker-compose with Neo4j 5.15"
```

---

## Phase 2: Backend Foundation

### Task 3: FastAPI project scaffold

**Files:**
- Create: `backend/src/main.py`
- Create: `backend/src/core/config.py`
- Create: `backend/src/core/__init__.py`
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`

**Step 1: Write pyproject.toml**

```toml
[tool.poetry]
name = "graphrag-neo4j-backend"
version = "0.1.0"
description = "Graph RAG over Papers With Code data"
authors = []
# Install all top-level packages found under src/ into the venv
# This makes `from library.rag.embedder import ...` work in poetry run commands
packages = [
  {include = "core",    from = "src"},
  {include = "dbase",   from = "src"},
  {include = "library", from = "src"},
  {include = "modules", from = "src"},
]

[tool.poetry.dependencies]
python            = "^3.11"
fastapi           = "0.111.0"
uvicorn           = {version = "0.29.0", extras = ["standard"]}
neo4j             = "5.19.0"
openai            = "1.30.0"
pydantic          = "2.7.0"
pydantic-settings = "2.2.1"
python-dotenv     = "1.0.1"
tqdm              = "4.66.4"

[tool.poetry.group.dev.dependencies]
pytest            = ">=8.0"
pytest-asyncio    = ">=0.23"
pytest-cov        = ">=5.0"
pytest-bdd        = ">=7.0"
httpx             = ">=0.27"

[build-system]
requires      = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
pythonpath   = ["src"]
testpaths    = ["tests"]
asyncio_mode = "auto"
```

**Step 2: Write src/core/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    llm_model: str = "gpt-4o-mini"
    top_k_seed_nodes: int = 5
    traversal_depth: int = 2

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 3: Write src/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Graph RAG Neo4j", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

**Step 4: Write Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install poetry && poetry install --no-root
COPY . .
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--app-dir", "src"]
```

**Step 5: Run locally to verify**

```bash
cd backend
poetry install
poetry run uvicorn main:app --reload --app-dir src
# curl http://localhost:8000/api/health
```

Expected: `{"status": "ok", "version": "0.1.0"}`

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: FastAPI scaffold with health endpoint"
```

---

### Task 4: Neo4j client + schema setup

**Files:**
- Create: `backend/src/dbase/neo4j/client.py`
- Create: `backend/src/library/graph/schema.py`
- Create: `backend/src/library/graph/__init__.py`

**Step 1: Write dbase/neo4j/client.py**

```python
from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
        )

    def close(self):
        self._driver.close()

    def verify_connection(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def run_query(self, cypher: str, params: dict = None):
        with self._driver.session() as session:
            return list(session.run(cypher, params or {}))
```

**Step 2: Write library/graph/schema.py**

```python
from dbase.neo4j.client import Neo4jClient
from core.config import settings

CONSTRAINTS = [
    "CREATE CONSTRAINT paper_id   IF NOT EXISTS FOR (p:Paper)   REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT method_id  IF NOT EXISTS FOR (m:Method)  REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT task_id    IF NOT EXISTS FOR (t:Task)    REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
]

VECTOR_INDEXES = [
    ("paper_embeddings",   "Paper",   "embedding"),
    ("method_embeddings",  "Method",  "embedding"),
    ("task_embeddings",    "Task",    "embedding"),
    ("dataset_embeddings", "Dataset", "embedding"),
]

def create_schema(client: Neo4jClient):
    for constraint in CONSTRAINTS:
        client.run_query(constraint)
        print(f"✓ {constraint[:60]}...")

    for name, label, prop in VECTOR_INDEXES:
        client.run_query(f"""
            CREATE VECTOR INDEX {name} IF NOT EXISTS
            FOR (n:{label}) ON (n.{prop})
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {settings.embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}}}
        """)
        print(f"✓ Vector index: {name}")

if __name__ == "__main__":
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    create_schema(client)
    print("Schema setup complete.")
```

**Step 3: Run schema setup**

```bash
cd backend
poetry run python src/library/graph/schema.py
```

Expected: constraints + indexes created. Verify in Neo4j browser with `:schema`.

**Step 4: Commit**

```bash
git add backend/src/dbase/ backend/src/library/graph/
git commit -m "feat: Neo4j client and schema with vector indexes"
```

---

## Phase 3: Data Ingestion

### Task 5: Download Papers With Code data

**Files:**
- Create: `data/download.sh`

**Step 1: Write download.sh**

```bash
#!/bin/bash
set -e
BASE="https://production-media.paperswithcode.com/about"
curl -L "$BASE/papers-with-abstracts.json.gz" -o data/papers.json.gz
curl -L "$BASE/methods.json.gz"               -o data/methods.json.gz
curl -L "$BASE/tasks.json.gz"                 -o data/tasks.json.gz
curl -L "$BASE/datasets.json.gz"              -o data/datasets.json.gz
curl -L "$BASE/evaluation-tables.json.gz"     -o data/evaluations.json.gz
gunzip -f data/*.gz
echo "Done:" && ls -lh data/*.json
```

**Step 2: Run**

```bash
chmod +x data/download.sh && bash data/download.sh
```

**Step 3: Inspect structure**

```bash
python3 -c "
import json
with open('data/papers.json') as f:
    d = json.load(f)
print(type(d), len(d))
print(list(d[0].keys()))
"
```

Note exact field names — use them in parser.

**Step 4: Commit**

```bash
git add data/download.sh
git commit -m "chore: add Papers With Code download script"
```

---

### Task 6: Parser — extract clean entities

**Files:**
- Create: `backend/src/library/graph/parser.py`

**Step 1: Write library/graph/parser.py**

```python
import json
from pathlib import Path
from typing import Iterator

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
# parser.py lives at: backend/src/library/graph/parser.py
# .parent×5 walks up to repo root, then /data → graphrag-neo4j/data/
MAX_PAPERS = 5000

def _load(filename: str) -> list:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)

def iter_papers() -> Iterator[dict]:
    for p in _load("papers.json")[:MAX_PAPERS]:
        if not p.get("title") or not p.get("abstract"):
            continue
        yield {
            "id":       p.get("paper_url", p.get("id", "")),
            "title":    p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year":     p.get("published", "")[:4],
            "url":      p.get("paper_url", ""),
        }

def iter_methods() -> Iterator[dict]:
    for m in _load("methods.json"):
        if not m.get("name"):
            continue
        yield {
            "id":          m.get("id", m["name"]),
            "name":        m["name"].strip(),
            "full_name":   m.get("full_name", m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }

def iter_tasks() -> Iterator[dict]:
    for t in _load("tasks.json"):
        if not t.get("name"):
            continue
        yield {
            "id":          t.get("id", t["name"]),
            "name":        t["name"].strip(),
            "area":        t.get("area", "").strip(),
            "description": (t.get("description") or "")[:1000],
        }

def iter_datasets() -> Iterator[dict]:
    for d in _load("datasets.json"):
        if not d.get("name"):
            continue
        yield {
            "id":          d.get("id", d["name"]),
            "name":        d["name"].strip(),
            "description": (d.get("description") or "")[:1000],
            "modalities":  ", ".join(d.get("modalities", [])),
        }
```

**Step 2: Smoke test**

```bash
cd backend
poetry run python -c "
from library.graph.parser import iter_papers, iter_methods, iter_tasks, iter_datasets
print(len(list(iter_papers())), len(list(iter_methods())),
      len(list(iter_tasks())), len(list(iter_datasets())))
"
```

Expected: 4 counts printed, no errors.

**Step 3: Commit**

```bash
git add backend/src/library/graph/parser.py
git commit -m "feat: Papers With Code entity parser"
```

---

### Task 7: Embedder module

**Files:**
- Create: `backend/src/library/rag/__init__.py`
- Create: `backend/src/library/rag/embedder.py`

**Step 1: Write library/rag/embedder.py**

```python
from openai import OpenAI
from core.config import settings

_client = OpenAI(api_key=settings.openai_api_key)

def embed_text(text: str) -> list[float]:
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * settings.embedding_dim
    response = _client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding

def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    results = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip() for t in texts[i:i+batch_size]]
        response = _client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        results.extend([d.embedding for d in response.data])
    return results
```

**Step 2: Test**

```bash
cd backend
poetry run python -c "
from library.rag.embedder import embed_text
v = embed_text('transformer for NLP')
print(f'dim={len(v)}, sample={v[:3]}')
"
```

Expected: `dim=1536`

**Step 3: Commit**

```bash
git add backend/src/library/rag/
git commit -m "feat: OpenAI embedder with batch support"
```

---

### Task 8: Ingest entities + relationships into Neo4j

**Files:**
- Create: `backend/src/library/graph/ingest.py`

**Step 1: Write library/graph/ingest.py**

```python
"""
Load all entities into Neo4j with embeddings.
Run once: poetry run python src/library/graph/ingest.py
Expected: ~30 min (embedding API calls)
"""
import json
from pathlib import Path
from tqdm import tqdm
from dbase.neo4j.client import Neo4jClient
from core.config import settings
from library.graph.parser import iter_papers, iter_methods, iter_tasks, iter_datasets
from library.rag.embedder import embed_batch

BATCH = 50

def _upsert_nodes(client: Neo4jClient, label: str, nodes: list[dict]):
    texts = [
        f"{n.get('title', n.get('name', ''))} {n.get('abstract', n.get('description', ''))}"
        for n in nodes
    ]
    embeddings = embed_batch(texts)
    records = [{**node, "embedding": emb} for node, emb in zip(nodes, embeddings)]
    props = list(nodes[0].keys()) + ["embedding"]
    set_clause = " ".join([f"n.{p} = row.{p}," for p in props]).rstrip(",")
    client.run_query(
        f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET {set_clause}",
        {"rows": records},
    )

def ingest_all(client: Neo4jClient):
    for label, iterator in [
        ("Paper",   iter_papers),
        ("Method",  iter_methods),
        ("Task",    iter_tasks),
        ("Dataset", iter_datasets),
    ]:
        print(f"Ingesting {label}s...")
        batch = []
        for node in tqdm(iterator()):
            batch.append(node)
            if len(batch) == BATCH:
                _upsert_nodes(client, label, batch)
                batch = []
        if batch:
            _upsert_nodes(client, label, batch)
        print(f"✓ {label} done")

def ingest_relationships(client: Neo4jClient):
    print("Ingesting relationships...")
    with open(Path("../data/evaluations.json")) as f:
        evals = json.load(f)
    for ev in tqdm(evals[:10000]):
        task_name    = ev.get("task",    {}).get("task_name",    "")
        dataset_name = ev.get("dataset", {}).get("dataset_name", "")
        if not task_name or not dataset_name:
            continue
        client.run_query(
            "MERGE (t:Task {id: $id}) ON CREATE SET t.name = $name",
            {"id": task_name, "name": task_name},
        )
        client.run_query("""
            MATCH (d:Dataset {name: $dname})
            MATCH (t:Task    {name: $tname})
            MERGE (d)-[:USED_FOR]->(t)
        """, {"dname": dataset_name, "tname": task_name})
        for row in ev.get("sota_rows", [])[:5]:
            method_name = row.get("method_name", "")
            if not method_name:
                continue
            for metric in row.get("metrics", []):
                client.run_query("""
                    MATCH (m:Method  {name: $mname})
                    MATCH (d:Dataset {name: $dname})
                    MERGE (m)-[r:EVALUATED_ON {metric: $metric}]->(d)
                    SET r.score = $score
                """, {
                    "mname":  method_name,
                    "dname":  dataset_name,
                    "metric": metric.get("metric", ""),
                    "score":  str(metric.get("value", "")),
                })
    print("✓ Relationships done")

if __name__ == "__main__":
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    ingest_all(client)
    ingest_relationships(client)
    print("\n✅ Ingestion complete.")
```

**Step 2: Run**

```bash
cd backend && poetry run python src/library/graph/ingest.py
```

**Step 3: Verify in Neo4j browser**

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC
```

Expected: Papers ~5000, Methods ~1000+, Tasks ~500+, Datasets ~500+.

**Step 4: Commit**

```bash
git add backend/src/library/graph/ingest.py
git commit -m "feat: entity ingestion pipeline with embeddings"
```

---

## Phase 4: Graph RAG Core

### Task 9: Vector retriever + graph traversal

**Files:**
- Create: `backend/src/library/rag/retriever.py`

**Step 1: Write library/rag/retriever.py**

```python
from dataclasses import dataclass, field
from dbase.neo4j.client import Neo4jClient
from core.config import settings
from library.rag.embedder import embed_text

@dataclass
class SeedNode:
    id: str
    label: str
    name: str
    score: float
    properties: dict = field(default_factory=dict)

@dataclass
class SubgraphEdge:
    from_id: str
    to_id: str
    type: str
    properties: dict = field(default_factory=dict)

@dataclass
class RetrievedSubgraph:
    seed_nodes: list[SeedNode]
    nodes: list[dict]
    edges: list[SubgraphEdge]
    cypher_used: str

INDEXES = [
    ("paper_embeddings",   "Paper"),
    ("method_embeddings",  "Method"),
    ("task_embeddings",    "Task"),
    ("dataset_embeddings", "Dataset"),
]

def _vector_search(client: Neo4jClient, vec: list[float], index: str, label: str, k: int) -> list[SeedNode]:
    rows = client.run_query(f"""
        CALL db.index.vector.queryNodes('{index}', {k}, $vec)
        YIELD node, score
        RETURN node.id AS id, node.name AS name,
               node.title AS title, score,
               properties(node) AS props
    """, {"vec": vec})
    results = []
    for r in rows:
        props = {k: v for k, v in dict(r["props"]).items() if k != "embedding"}
        results.append(SeedNode(
            id=r["id"], label=label,
            name=r["name"] or r["title"] or "",
            score=r["score"], properties=props,
        ))
    return results

def find_seed_nodes(client: Neo4jClient, question: str) -> list[SeedNode]:
    vec = embed_text(question)
    k   = settings.top_k_seed_nodes
    all_seeds = []
    for index, label in INDEXES:
        all_seeds.extend(_vector_search(client, vec, index, label, k))
    all_seeds.sort(key=lambda n: n.score, reverse=True)
    return all_seeds[:k]

TRAVERSE_CYPHER = """
    MATCH (seed) WHERE seed.id IN $ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN seed,
           collect(DISTINCT {from: seed.id, to: n1.id, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT n1) AS nodes1,
           collect(DISTINCT {from: n1.id,  to: n2.id, type: type(r2), props: properties(r2)}) AS e2,
           collect(DISTINCT n2) AS nodes2
"""

def traverse_from_seeds(client: Neo4jClient, seeds: list[SeedNode]) -> RetrievedSubgraph:
    rows = client.run_query(TRAVERSE_CYPHER, {"ids": [s.id for s in seeds]})
    all_nodes, all_edges = {}, []
    for r in rows:
        for n in [r["seed"]] + (r["nodes1"] or []) + (r["nodes2"] or []):
            if n is None:
                continue
            d = {k: v for k, v in dict(n).items() if k != "embedding"}
            all_nodes[d.get("id", "")] = d
        for e in (r["e1"] or []) + (r["e2"] or []):
            if e.get("from") and e.get("to") and e.get("type"):
                all_edges.append(SubgraphEdge(
                    from_id=e["from"], to_id=e["to"],
                    type=e["type"], properties=dict(e.get("props") or {}),
                ))
    return RetrievedSubgraph(
        seed_nodes=seeds,
        nodes=list(all_nodes.values()),
        edges=all_edges,
        cypher_used=TRAVERSE_CYPHER,
    )

def retrieve(client: Neo4jClient, question: str) -> RetrievedSubgraph:
    seeds = find_seed_nodes(client, question)
    return traverse_from_seeds(client, seeds)
```

**Step 2: Smoke test**

```bash
cd backend
poetry run python -c "
from library.rag.retriever import retrieve
from dbase.neo4j.client import Neo4jClient
from core.config import settings
client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
r = retrieve(client, 'methods for image segmentation')
print(f'Seeds: {len(r.seed_nodes)}, Nodes: {len(r.nodes)}, Edges: {len(r.edges)}')
for s in r.seed_nodes:
    print(f'  [{s.label}] {s.name} ({s.score:.3f})')
"
```

Expected: 5 seeds, 20+ nodes, edges printed.

**Step 3: Commit**

```bash
git add backend/src/library/rag/retriever.py
git commit -m "feat: vector retriever and graph traversal"
```

---

### Task 10: Context builder + LLM answer generator

**Files:**
- Create: `backend/src/library/rag/generator.py`

**Step 1: Write library/rag/generator.py**

```python
from openai import OpenAI
from core.config import settings
from library.rag.retriever import RetrievedSubgraph

_client = OpenAI(api_key=settings.openai_api_key)

SYSTEM = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""

def _build_context(sg: RetrievedSubgraph) -> str:
    lines = ["=== GRAPH CONTEXT ===", "SEED NODES:"]
    for s in sg.seed_nodes:
        lines.append(f"  [{s.label}] {s.name} (score={s.score:.2f})")
    lines.append("\nRELATIONSHIPS:")
    for e in sg.edges[:30]:
        props = f" {e.properties}" if e.properties else ""
        lines.append(f"  ({e.from_id}) -[{e.type}]-> ({e.to_id}){props}")
    return "\n".join(lines)

def generate_answer(question: str, sg: RetrievedSubgraph) -> str:
    context = _build_context(sg)
    res = _client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return res.choices[0].message.content
```

**Step 2: End-to-end test**

```bash
cd backend
poetry run python -c "
from library.rag.retriever import retrieve
from library.rag.generator import generate_answer
from dbase.neo4j.client import Neo4jClient
from core.config import settings
client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
q = 'What methods are used for object detection?'
sg = retrieve(client, q)
print(generate_answer(q, sg))
"
```

Expected: Coherent answer mentioning graph entities.

**Step 3: Commit**

```bash
git add backend/src/library/rag/generator.py
git commit -m "feat: context builder and LLM answer generator"
```

---

## Phase 5: FastAPI Routes

### Task 11: API routes

**Files:**
- Create: `backend/src/router.py`
- Modify: `backend/src/main.py`

**Step 1: Write src/router.py**

```python
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from library.rag.retriever import retrieve
from library.rag.generator import generate_answer
from dbase.neo4j.client import Neo4jClient
from core.config import settings

router = APIRouter(prefix="/api")

def get_neo4j_client() -> Neo4jClient:
    return Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

class QueryRequest(BaseModel):
    question: str

class NodeOut(BaseModel):
    id: str
    label: str
    name: str
    score: float | None = None

class EdgeOut(BaseModel):
    from_id: str
    to_id: str
    type: str
    properties: dict = {}

class QueryResponse(BaseModel):
    answer: str
    seed_nodes: list[NodeOut]
    nodes: list[dict]
    edges: list[EdgeOut]
    cypher_used: str
    latency_ms: int

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, client: Neo4jClient = Depends(get_neo4j_client)):
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")
    t0 = time.time()
    sg     = retrieve(client, req.question)
    answer = generate_answer(req.question, sg)
    return QueryResponse(
        answer=answer,
        seed_nodes=[NodeOut(id=s.id, label=s.label, name=s.name, score=s.score)
                    for s in sg.seed_nodes],
        nodes=sg.nodes,
        edges=[EdgeOut(from_id=e.from_id, to_id=e.to_id,
                       type=e.type, properties=e.properties)
               for e in sg.edges],
        cypher_used=sg.cypher_used,
        latency_ms=int((time.time() - t0) * 1000),
    )

@router.get("/graph/schema")
async def get_schema(client: Neo4jClient = Depends(get_neo4j_client)):
    labels = client.run_query("CALL db.labels() YIELD label RETURN collect(label) AS l")
    rels   = client.run_query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS r")
    return {
        "node_labels":         labels[0]["l"] if labels else [],
        "relationship_types":  rels[0]["r"]   if rels   else [],
    }

@router.get("/graph/explore")
async def explore(limit: int = 50, client: Neo4jClient = Depends(get_neo4j_client)):
    rows = client.run_query("""
        MATCH (a)-[r]->(b)
        RETURN a, type(r) AS rel, b LIMIT $limit
    """, {"limit": limit})
    nodes, edges = {}, []
    for row in rows:
        for n in [row["a"], row["b"]]:
            d = {k: v for k, v in dict(n).items() if k != "embedding"}
            nid = d.get("id", d.get("name", ""))
            nodes[nid] = {**d, "label": list(n.labels)[0]}
        edges.append({"from": dict(row["a"]).get("id",""),
                      "to":   dict(row["b"]).get("id",""),
                      "type": row["rel"]})
    return {"nodes": list(nodes.values()), "edges": edges}

@router.get("/health")
async def health(client: Neo4jClient = Depends(get_neo4j_client)):
    return {"status": "ok", "neo4j": "connected" if client.verify_connection() else "error"}
```

**Step 2: Update src/main.py to include router**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(title="Graph RAG Neo4j", version="0.1.0")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
```

**Step 3: Test all endpoints**

```bash
poetry run uvicorn main:app --reload --app-dir src

curl http://localhost:8000/api/health
curl http://localhost:8000/api/graph/schema
curl http://localhost:8000/api/graph/explore?limit=5
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "methods for object detection"}'
```

Expected: All return valid JSON.

**Step 4: Commit**

```bash
git add backend/src/router.py backend/src/main.py
git commit -m "feat: FastAPI routes for query, schema, and explore"
```

---

## Phase 6: Vite + React Frontend

### Task 12: Vite scaffold + Tailwind + shadcn/ui + types + API client

**Files:**
- Create: `frontend/` (Vite + React app)
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/.env.local`

**Step 1: Scaffold Vite + React + TypeScript**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-force-graph-2d
```

**Step 2: Install Tailwind**

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

Add to `src/index.css` (top):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 3: Init shadcn**

```bash
# Note: use 'shadcn' (not 'shadcn-ui' — that package is deprecated)
npx shadcn@latest init
# Prompts: style=Default, base color=Slate, CSS variables=yes
```

**Step 4: Add needed shadcn components**

```bash
npx shadcn@latest add card button badge input collapsible scroll-area tooltip
```

Components land in `src/components/ui/`.

**Step 5: Write src/lib/types.ts**

```typescript
export interface SeedNode {
  id: string; label: string; name: string; score: number
}
export interface GraphNode {
  id: string; name?: string; title?: string; label?: string
  [key: string]: unknown
}
export interface GraphEdge {
  from_id: string; to_id: string; type: string
  properties: Record<string, unknown>
}
export interface QueryResponse {
  answer: string; seed_nodes: SeedNode[]
  nodes: GraphNode[]; edges: GraphEdge[]
  cypher_used: string; latency_ms: number
}
```

**Step 6: Write src/lib/api.ts**

```typescript
import { QueryResponse } from './types'

// Vite env vars must be prefixed VITE_ (not NEXT_PUBLIC_)
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function queryGraph(question: string): Promise<QueryResponse> {
  const res = await fetch(`${BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
```

**Step 7: Create .env.local**

```bash
VITE_API_URL=http://localhost:8000
```

**Step 8: Verify Tailwind + shadcn work**

```bash
npm run dev
# Open: http://localhost:5173
```

Expected: Vite default page loads (no errors in console).

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Vite + React scaffold with Tailwind and shadcn/ui"
```

---

### Task 13: ChatPanel component (shadcn/ui)

**Files:**
- Create: `frontend/src/components/ChatPanel.tsx`

**Step 1: Write ChatPanel.tsx**

No `'use client'` — Vite is a pure SPA. Use shadcn `Input`, `Button`, `Badge`, `ScrollArea`.

```typescript
import { useState } from 'react'
import { queryGraph } from '@/lib/api'
import { QueryResponse } from '@/lib/types'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

const EXAMPLES = [
  'What methods are used for object detection?',
  'Which papers introduced transformer models for NLP?',
  'What datasets benchmark image segmentation?',
  'Find variants of BERT and the tasks they solve.',
]

const LABEL_COLORS: Record<string, string> = {
  Paper: 'bg-blue-100 text-blue-700',
  Method: 'bg-green-100 text-green-700',
  Task: 'bg-amber-100 text-amber-700',
  Dataset: 'bg-purple-100 text-purple-700',
}

interface Props {
  onResult: (r: QueryResponse) => void
  isLoading: boolean
  setIsLoading: (v: boolean) => void
}

export default function ChatPanel({ onResult, isLoading, setIsLoading }: Props) {
  const [q, setQ]             = useState('')
  const [answer, setAnswer]   = useState('')
  const [latency, setLatency] = useState<number | null>(null)
  const [seeds, setSeeds]     = useState<QueryResponse['seed_nodes']>([])
  const [error, setError]     = useState('')

  async function submit(question: string) {
    if (!question.trim() || isLoading) return
    setIsLoading(true); setError('')
    try {
      const res = await queryGraph(question)
      setAnswer(res.answer)
      setLatency(res.latency_ms)
      setSeeds(res.seed_nodes)
      onResult(res)
    } catch {
      setError('Backend unreachable. Is the server running?')
    } finally { setIsLoading(false) }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <h2 className="font-semibold text-gray-800">Ask the Knowledge Graph</h2>

      {/* Example questions */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map(e => (
          <button key={e} onClick={() => { setQ(e); submit(e) }}
            className="text-xs px-2 py-1 bg-slate-100 text-slate-700 rounded-full hover:bg-slate-200 transition-colors">
            {e}
          </button>
        ))}
      </div>

      {/* Input row */}
      <div className="flex gap-2">
        <Input
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit(q)}
          placeholder="Ask about ML papers, methods, datasets..."
        />
        <Button onClick={() => submit(q)} disabled={isLoading}>
          {isLoading ? '...' : 'Ask'}
        </Button>
      </div>

      {/* Seed node badges */}
      {seeds.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-gray-400">Matched:</span>
          {seeds.map(s => (
            <Badge key={s.id} className={LABEL_COLORS[s.label] ?? ''} variant="outline">
              {s.label}: {s.name} ({s.score.toFixed(2)})
            </Badge>
          ))}
        </div>
      )}

      {/* Answer */}
      {answer && (
        <ScrollArea className="flex-1 bg-slate-50 rounded-lg p-4 text-sm">
          <div className="text-xs text-gray-400 mb-1">
            Answer {latency != null && `· ${latency}ms`}
          </div>
          <p className="whitespace-pre-wrap text-gray-700">{answer}</p>
        </ScrollArea>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{error}</div>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx
git commit -m "feat: ChatPanel with shadcn Input, Button, Badge, ScrollArea"
```

---

### Task 14: GraphViewer + CypherPanel + App layout

**Files:**
- Create: `frontend/src/components/GraphViewer.tsx`
- Create: `frontend/src/components/CypherPanel.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write GraphViewer.tsx**

No `next/dynamic` needed — Vite is browser-only, direct import works.

```typescript
import { useRef, useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { GraphNode, GraphEdge, SeedNode } from '@/lib/types'

const COLORS: Record<string, string> = {
  Paper: '#3b82f6', Method: '#10b981', Task: '#f59e0b', Dataset: '#8b5cf6',
}

interface Props { nodes: GraphNode[]; edges: GraphEdge[]; seedNodes: SeedNode[] }

export default function GraphViewer({ nodes, edges, seedNodes }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 700, height: 480 })
  const seedIds = new Set(seedNodes.map(s => s.id))

  useEffect(() => {
    if (!containerRef.current) return
    const { offsetWidth, offsetHeight } = containerRef.current
    setDimensions({ width: offsetWidth, height: offsetHeight })
  }, [nodes])

  if (!nodes.length) return (
    <div className="flex items-center justify-center h-full text-gray-400 text-sm">
      Ask a question to see the knowledge graph
    </div>
  )

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        graphData={{
          nodes: nodes.map(n => ({
            id: n.id,
            name: n.name || n.title || n.id,
            label: n.label ?? 'Node',
            val: seedIds.has(n.id as string) ? 3 : 1,
          })),
          links: edges.map(e => ({ source: e.from_id, target: e.to_id, label: e.type })),
        }}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel="name"
        nodeColor={n => seedIds.has((n as {id: string}).id)
          ? '#f97316'
          : COLORS[(n as {label: string}).label] ?? '#6b7280'}
        nodeRelSize={6}
        linkLabel="label"
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkColor={() => '#d1d5db'}
      />
    </div>
  )
}
```

**Step 2: Write CypherPanel.tsx (shadcn Collapsible)**

```typescript
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'

export default function CypherPanel({ cypher }: { cypher: string }) {
  const [open, setOpen] = useState(false)
  if (!cypher) return null

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="border-t border-gray-200">
      <CollapsibleTrigger className="w-full flex items-center gap-2 px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Cypher query used
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="px-4 py-3 bg-gray-900 text-green-400 text-xs overflow-x-auto font-mono">
          {cypher}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  )
}
```

**Step 3: Write src/App.tsx (main layout)**

```typescript
import { useState } from 'react'
import { Card } from '@/components/ui/card'
import ChatPanel from '@/components/ChatPanel'
import GraphViewer from '@/components/GraphViewer'
import CypherPanel from '@/components/CypherPanel'
import { QueryResponse } from '@/lib/types'

export default function App() {
  const [result, setResult]       = useState<QueryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center gap-3">
        <span className="text-xl">🧠</span>
        <h1 className="font-semibold text-gray-900">Graph RAG Explorer</h1>
        <span className="text-xs text-gray-400 ml-2">
          ML Knowledge Graph · Neo4j + OpenAI
        </span>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden p-4 gap-4">
        {/* Left: Chat */}
        <Card className="w-2/5 flex flex-col overflow-hidden">
          <ChatPanel
            onResult={setResult}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
          />
        </Card>

        {/* Right: Graph + Cypher */}
        <Card className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                Retrieving from knowledge graph...
              </div>
            ) : (
              <GraphViewer
                nodes={result?.nodes ?? []}
                edges={result?.edges ?? []}
                seedNodes={result?.seed_nodes ?? []}
              />
            )}
          </div>
          <CypherPanel cypher={result?.cypher_used ?? ''} />
        </Card>
      </div>
    </div>
  )
}
```

**Step 4: Install lucide-react (for Collapsible icons)**

```bash
npm install lucide-react
```

**Step 5: Run and verify**

```bash
cd frontend
npm run dev
# Open: http://localhost:5173
```

Expected: UI loads, ask question → answer + graph + seed badges + Cypher panel.

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: GraphViewer, CypherPanel (shadcn Collapsible), App layout"
```

---

## Phase 7: Polish & Finalization

### Task 15: Full Docker Compose + README

**Step 1: Full stack test**

```bash
cd ~/projects/graphrag-neo4j
docker compose up --build
# Open: http://localhost:3000
```

Verify: Ask a question → answer appears, graph renders, Cypher panel expands.

**Step 2: Write README.md**

```markdown
# graphrag-neo4j

Full-stack **Graph RAG** using Neo4j as a unified graph + vector store.
Ask natural language questions about the ML research landscape —
the system retrieves a knowledge subgraph and generates grounded answers.

## Why Graph RAG (not just RAG)

Traditional RAG retrieves *similar text chunks*.
This retrieves a *knowledge subgraph* — enabling multi-hop reasoning
that vector search cannot do alone.

## Stack

| Layer | Tech |
|-------|------|
| Graph + Vector DB | Neo4j 5.15 |
| Backend | FastAPI + Python 3.11 |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui |
| LLM + Embeddings | OpenAI GPT-4o-mini + text-embedding-3-small |
| Visualization | react-force-graph-2d |
| Infra | Docker Compose |

## Quick Start

```bash
git clone https://github.com/nunenuh/graphrag-neo4j
cd graphrag-neo4j
cp .env.example .env      # add OPENAI_API_KEY
docker compose up neo4j -d
cd backend && poetry run python src/library/graph/schema.py
bash data/download.sh
poetry run python src/library/graph/ingest.py    # ~30 min
docker compose up --build
# Open: http://localhost:3000
```

## Example Questions

- *"What methods are used for object detection?"*
- *"Which papers introduced transformer-based NLP models?"*
- *"What datasets benchmark image segmentation?"*
- *"Find BERT variants and the tasks they solve."*
```

**Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: README with architecture, quickstart, and examples"
git tag v0.1.0
```

---

## Summary

| Phase | Tasks | Output |
|-------|-------|--------|
| 1 — Infrastructure | 1–2 | Docker + Neo4j running |
| 2 — Backend foundation | 3–4 | FastAPI + Neo4j client + vector schema |
| 3 — Data ingestion | 5–8 | 5k papers embedded + loaded into Neo4j |
| 4 — Graph RAG core | 9–10 | Retriever + generator working end-to-end |
| 5 — API routes | 11 | `/api/query`, `/api/graph/schema`, `/api/graph/explore` |
| 6 — Frontend | 12–14 | Vite + React + shadcn/ui: chat + force graph + Cypher panel |
| 7 — Polish | 15 | Full Docker Compose + README |

**Estimated:** 6–10 hours active work (+ ~30 min ingestion wait)
