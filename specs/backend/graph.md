# Backend Spec: Graph Layer

Files: `backend/src/library/graph/schema.py`, `backend/src/library/graph/parser.py`

See also: [[projects/graphrag-neo4j/docs/technical/data-model]]

---

## Responsibility

| File | Does |
|------|------|
| `src/library/graph/schema.py` | Creates Neo4j constraints and vector indexes (one-time setup) |
| `src/library/graph/parser.py` | Parses Papers With Code JSON files into clean entity dicts |

The graph layer **never** writes to Neo4j directly — that's `src/library/graph/ingest.py`'s job.
The graph layer **never** embeds — that's `src/library/rag/embedder.py`'s job.

---

## Node Types & Properties

### `:Paper`
```python
{
    "id": str,          # Derived from paper_url slug (e.g. "attention-is-all-you-need")
    "title": str,       # Paper title
    "abstract": str,    # Abstract text (may be empty string, never None)
    "url": str,         # Full PwC URL
    "year": int | None, # Publication year
    "embedding": list[float]  # Set during ingest, not during parsing
}
```

### `:Method`
```python
{
    "id": str,          # Slugified method name (e.g. "transformer")
    "name": str,        # Display name
    "description": str, # May be empty string
    "embedding": list[float]
}
```

### `:Task`
```python
{
    "id": str,          # Slugified task name (e.g. "image-classification")
    "name": str,
    "description": str,
    "embedding": list[float]
}
```

### `:Dataset`
```python
{
    "id": str,          # Slugified dataset name (e.g. "imagenet")
    "name": str,
    "description": str,
    "embedding": list[float]
}
```

---

## Relationships

| Relationship | From → To | Properties |
|-------------|-----------|------------|
| `INTRODUCES` | `:Paper` → `:Method` | none |
| `ADDRESSES` | `:Paper` → `:Task` | none |
| `APPLIED_ON` | `:Method` → `:Dataset` | none |
| `EVALUATED_ON` | `:Paper` → `:Dataset` | `metric: str`, `score: str` |
| `USED_FOR` | `:Method` → `:Task` | none |
| `VARIANT_OF` | `:Method` → `:Method` | none |
| `SUBTASK_OF` | `:Task` → `:Task` | none |

---

## `schema.py` — Constraints & Vector Indexes

```python
"""
library/graph/schema.py

Creates Neo4j constraints and vector indexes.
Run once before ingestion: python src/library/graph/schema.py
"""
import logging
from core.config import settings
from dbase.neo4j.client import Neo4jClient

logger = logging.getLogger(__name__)


CONSTRAINTS = [
    "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT method_id IF NOT EXISTS FOR (m:Method) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
]

VECTOR_INDEXES = [
    """
    CREATE VECTOR INDEX paper_embeddings IF NOT EXISTS
    FOR (p:Paper) ON p.embedding
    OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """,
    """
    CREATE VECTOR INDEX method_embeddings IF NOT EXISTS
    FOR (m:Method) ON m.embedding
    OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """,
    """
    CREATE VECTOR INDEX task_embeddings IF NOT EXISTS
    FOR (t:Task) ON t.embedding
    OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """,
    """
    CREATE VECTOR INDEX dataset_embeddings IF NOT EXISTS
    FOR (d:Dataset) ON d.embedding
    OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """,
]


def setup_schema(client: Neo4jClient) -> None:
    """Create all constraints and vector indexes."""
    for cypher in CONSTRAINTS:
        client.run_query(cypher)
        logger.info(f"Constraint applied")

    for cypher in VECTOR_INDEXES:
        client.run_query(cypher)
        logger.info(f"Vector index applied")


if __name__ == "__main__":
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    setup_schema(client)
    logger.info("Schema setup complete")
```

**Rules:**
- Use `IF NOT EXISTS` on all constraints and indexes — safe to re-run
- Vector dimension is always 1536 (`text-embedding-3-small`)
- Similarity function is always `cosine`

---

## `parser.py` — PwC JSON → Entity Dicts

```python
"""
library/graph/parser.py

Parse Papers With Code JSON files into clean entity dictionaries.
Returns pure Python dicts — no Neo4j driver objects, no embeddings.
"""
import json
import logging
import re
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to lowercase slug: 'BERT Model' → 'bert-model'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_papers(path: Path) -> Iterator[dict]:
    """
    Parse papers.json into Paper entity dicts.

    Yields one dict per paper with normalized fields.
    Skips entries with missing title.
    """
    with path.open() as f:
        data = json.load(f)

    for raw in data:
        title = raw.get("title", "").strip()
        if not title:
            continue

        url = raw.get("paper_url", "")
        paper_id = url.rstrip("/").split("/")[-1] if url else slugify(title)

        yield {
            "id": paper_id,
            "title": title,
            "abstract": raw.get("abstract", "") or "",
            "url": url,
            "year": raw.get("year"),
        }


def parse_methods(path: Path) -> Iterator[dict]:
    """Parse methods.json into Method entity dicts."""
    with path.open() as f:
        data = json.load(f)

    for raw in data:
        name = raw.get("name", "").strip()
        if not name:
            continue
        yield {
            "id": slugify(name),
            "name": name,
            "description": raw.get("description", "") or "",
        }


def parse_tasks(path: Path) -> Iterator[dict]:
    """Parse tasks.json into Task entity dicts."""
    with path.open() as f:
        data = json.load(f)

    for raw in data:
        name = raw.get("task", raw.get("name", "")).strip()
        if not name:
            continue
        yield {
            "id": slugify(name),
            "name": name,
            "description": raw.get("description", "") or "",
        }


def parse_datasets(path: Path) -> Iterator[dict]:
    """Parse datasets.json into Dataset entity dicts."""
    with path.open() as f:
        data = json.load(f)

    for raw in data:
        name = raw.get("name", "").strip()
        if not name:
            continue
        yield {
            "id": slugify(name),
            "name": name,
            "description": raw.get("description", "") or "",
        }


def parse_relationships(path: Path) -> Iterator[dict]:
    """
    Parse evaluations.json into relationship dicts.

    Yields:
        {
            "paper_id": str,
            "method_id": str,
            "task_id": str,
            "dataset_id": str,
            "metric": str,
            "score": str,
        }
    """
    with path.open() as f:
        data = json.load(f)

    for raw in data:
        paper_url = raw.get("paper_url", "")
        paper_id = paper_url.rstrip("/").split("/")[-1] if paper_url else ""

        method_name = raw.get("method", {}).get("name", "") if isinstance(raw.get("method"), dict) else ""
        task_name = raw.get("task", "")
        dataset_name = raw.get("dataset", "")

        if not all([paper_id, task_name, dataset_name]):
            continue

        yield {
            "paper_id": paper_id,
            "method_id": slugify(method_name) if method_name else "",
            "task_id": slugify(task_name),
            "dataset_id": slugify(dataset_name),
            "metric": raw.get("metric", "") or "",
            "score": str(raw.get("metric_result", "") or ""),
        }
```

**Parser Rules:**
- Always return new dicts — never mutate the raw input
- Use generator pattern (`Iterator[dict]`) — memory-efficient for 5k+ records
- Missing optional fields → empty string, never `None`
- IDs are always slugified (lowercase, hyphens)
- Skip records with missing required fields (title, name) with a log warning
- `parse_relationships` must handle both `"method": {...}` objects and `"method": "string"` from PwC's inconsistent JSON

---

## Cypher Query Patterns

### MERGE (upsert) — always use MERGE, never CREATE

```cypher
-- Create/update a Paper node
MERGE (p:Paper {id: $id})
SET p.title = $title,
    p.abstract = $abstract,
    p.url = $url,
    p.year = $year
```

### Set embedding (separate from node creation)

```cypher
MATCH (p:Paper {id: $id})
SET p.embedding = $embedding
```

### Create relationship

```cypher
MATCH (p:Paper {id: $paper_id})
MATCH (m:Method {id: $method_id})
MERGE (p)-[:INTRODUCES]->(m)
```

```cypher
MATCH (p:Paper {id: $paper_id})
MATCH (d:Dataset {id: $dataset_id})
MERGE (p)-[r:EVALUATED_ON]->(d)
SET r.metric = $metric, r.score = $score
```

**Rules:**
- Always `MERGE`, never `CREATE` for nodes (idempotent)
- `MERGE` on relationships after `MATCH`ing both endpoints
- Set properties with `SET` after MERGE (don't put them in the MERGE pattern unless they're identity)
- Parameterize all values — never string-interpolate into Cypher

---

## ID Generation Rules

| Entity | ID Rule | Example |
|--------|---------|---------|
| Paper | Last segment of `paper_url` | `"attention-is-all-you-need"` |
| Method | `slugify(name)` | `"transformer"` |
| Task | `slugify(task_name)` | `"image-classification"` |
| Dataset | `slugify(name)` | `"imagenet"` |

**`slugify` definition:**
```python
re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
```
