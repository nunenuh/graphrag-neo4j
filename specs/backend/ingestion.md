# Backend Spec: Ingestion Pipeline

File: `backend/src/library/graph/ingest.py`

See also: [[projects/graphrag-neo4j/specs/backend/graph]] · [[projects/graphrag-neo4j/specs/backend/rag]]

---

## Responsibility

`ingest.py` **orchestrates** the full ingestion pipeline:

```
PwC JSON files
    → parser.py      (parse raw JSON → entity dicts)
    → embedder.py    (batch embed via OpenAI)
    → dbase/neo4j/client   (MERGE nodes + SET embedding + create relationships)
```

`ingest.py` calls helpers — it does not contain parsing or embedding logic itself.

---

## Pipeline Phases

### Phase 1: Parse

Parse all 4 entity types from PwC JSON files.

```python
from pathlib import Path
from library.graph.parser import parse_papers, parse_methods, parse_tasks, parse_datasets, parse_relationships

DATA_DIR = Path("data/")

papers = list(parse_papers(DATA_DIR / "papers.json"))
methods = list(parse_methods(DATA_DIR / "methods.json"))
tasks = list(parse_tasks(DATA_DIR / "tasks.json"))
datasets = list(parse_datasets(DATA_DIR / "datasets.json"))
relationships = list(parse_relationships(DATA_DIR / "evaluations.json"))
```

### Phase 2: Embed

Embed each entity type using the text that best represents it.

| Entity | Text to embed |
|--------|--------------|
| `:Paper` | `f"{title}. {abstract}"` |
| `:Method` | `f"{name}. {description}"` |
| `:Task` | `f"{name}. {description}"` |
| `:Dataset` | `f"{name}. {description}"` |

Use `embedder.batch_embed()` — never embed one by one in a loop.

```python
from library.rag.embedder import batch_embed

paper_texts = [f"{p['title']}. {p['abstract']}" for p in papers]
paper_embeddings = batch_embed(paper_texts)  # list[list[float]]

# Zip back into entity dicts (immutable — create new dicts)
papers_with_embeddings = [
    {**paper, "embedding": emb}
    for paper, emb in zip(papers, paper_embeddings)
]
```

### Phase 3: Load Nodes

Load each entity type to Neo4j using MERGE + SET.

```python
from dbase.neo4j.client import Neo4jClient

def load_papers(client: Neo4jClient, papers: list[dict]) -> None:
    """Load Paper nodes with embeddings into Neo4j."""
    cypher = """
    UNWIND $papers AS p
    MERGE (n:Paper {id: p.id})
    SET n.title = p.title,
        n.abstract = p.abstract,
        n.url = p.url,
        n.year = p.year,
        n.embedding = p.embedding
    """
    client.run_query(cypher, {"papers": papers})
    logger.info(f"Loaded {len(papers)} Paper nodes")
```

Use `UNWIND $batch AS item` to batch-load — one query per entity type, not one query per record.

### Phase 4: Load Relationships

After all nodes are loaded, create relationships.

```python
def load_relationships(client: Neo4jClient, relationships: list[dict]) -> None:
    """Create all relationships from evaluations data."""
    # INTRODUCES: Paper → Method
    cypher_introduces = """
    UNWIND $rels AS r
    MATCH (p:Paper {id: r.paper_id})
    MATCH (m:Method {id: r.method_id})
    WHERE r.method_id <> ''
    MERGE (p)-[:INTRODUCES]->(m)
    """
    client.run_query(cypher_introduces, {"rels": relationships})

    # EVALUATED_ON: Paper → Dataset (with metric/score)
    cypher_evaluated = """
    UNWIND $rels AS r
    MATCH (p:Paper {id: r.paper_id})
    MATCH (d:Dataset {id: r.dataset_id})
    MERGE (p)-[rel:EVALUATED_ON]->(d)
    SET rel.metric = r.metric, rel.score = r.score
    """
    client.run_query(cypher_evaluated, {"rels": relationships})

    # ADDRESSES: Paper → Task
    cypher_addresses = """
    UNWIND $rels AS r
    MATCH (p:Paper {id: r.paper_id})
    MATCH (t:Task {id: r.task_id})
    MERGE (p)-[:ADDRESSES]->(t)
    """
    client.run_query(cypher_addresses, {"rels": relationships})
```

---

## Full Orchestration

```python
"""
library/graph/ingest.py

Orchestrates: parse → embed → load nodes → load relationships.
Run once: python src/library/graph/ingest.py
Expected duration: ~30 minutes for 5k papers (OpenAI rate limits).
"""
import logging
import time
from pathlib import Path

from core.config import settings
from dbase.neo4j.client import Neo4jClient
from library.graph.parser import (
    parse_datasets, parse_methods, parse_papers,
    parse_relationships, parse_tasks,
)
from library.rag.embedder import batch_embed

logger = logging.getLogger(__name__)
DATA_DIR = Path("data/")


def run_ingestion() -> None:
    """Run the full ingestion pipeline."""
    client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    start = time.time()

    # --- Parse ---
    logger.info("Parsing PwC JSON files...")
    papers = list(parse_papers(DATA_DIR / "papers.json"))
    methods = list(parse_methods(DATA_DIR / "methods.json"))
    tasks = list(parse_tasks(DATA_DIR / "tasks.json"))
    datasets = list(parse_datasets(DATA_DIR / "datasets.json"))
    relationships = list(parse_relationships(DATA_DIR / "evaluations.json"))
    logger.info(f"Parsed: {len(papers)} papers, {len(methods)} methods, "
                f"{len(tasks)} tasks, {len(datasets)} datasets")

    # --- Embed ---
    logger.info("Embedding entities (this takes ~20-25 min for 5k papers)...")
    papers = _attach_embeddings(papers, [f"{p['title']}. {p['abstract']}" for p in papers])
    methods = _attach_embeddings(methods, [f"{m['name']}. {m['description']}" for m in methods])
    tasks = _attach_embeddings(tasks, [f"{t['name']}. {t['description']}" for t in tasks])
    datasets = _attach_embeddings(datasets, [f"{d['name']}. {d['description']}" for d in datasets])

    # --- Load Nodes ---
    logger.info("Loading nodes to Neo4j...")
    load_papers(client, papers)
    load_methods(client, methods)
    load_tasks(client, tasks)
    load_datasets(client, datasets)

    # --- Load Relationships ---
    logger.info("Loading relationships to Neo4j...")
    load_relationships(client, relationships)

    elapsed = time.time() - start
    logger.info(f"Ingestion complete in {elapsed:.0f}s")


def _attach_embeddings(entities: list[dict], texts: list[str]) -> list[dict]:
    """Return new entity dicts with 'embedding' field attached."""
    embeddings = batch_embed(texts)
    return [{**entity, "embedding": emb} for entity, emb in zip(entities, embeddings)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ingestion()
```

---

## Batching Rules

**OpenAI embedding API limits:**
- `batch_size = 100` texts per API call
- Respect rate limits — see `library/rag/embedder.py` for retry/backoff logic
- Log progress every batch: `logger.info(f"Embedded batch {i}/{total_batches}")`

**Neo4j write limits:**
- Use `UNWIND $list` for bulk writes — one Cypher call per entity type
- Do NOT write one node per query (too slow for 5k+ records)
- Recommended Neo4j batch size: 500 nodes per `UNWIND` call (split list if needed)

```python
def _batch_write(client: Neo4jClient, cypher: str, items: list[dict], batch_size: int = 500) -> None:
    """Write items to Neo4j in batches."""
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        client.run_query(cypher, {"items": batch})
        logger.info(f"Wrote batch {i // batch_size + 1} ({len(batch)} items)")
```

---

## Error Handling

| Error | Action |
|-------|--------|
| OpenAI `RateLimitError` | Retry with exponential backoff (handled in `embedder.py`) |
| OpenAI `APIError` | Log + raise — stop ingestion, don't partial-load |
| Neo4j `ServiceUnavailable` | Retry 3 times with 5s sleep, then raise |
| Missing JSON field | Skip record, log warning, continue |
| `json.JSONDecodeError` | Raise immediately — file is corrupt |

**Ingestion is idempotent**: MERGE means re-running will update rather than duplicate nodes.

---

## Verification Queries

After ingestion, verify node counts:

```cypher
MATCH (p:Paper) RETURN count(p) AS papers
MATCH (m:Method) RETURN count(m) AS methods
MATCH (t:Task) RETURN count(t) AS tasks
MATCH (d:Dataset) RETURN count(d) AS datasets
MATCH ()-[r]->() RETURN count(r) AS relationships
```

Expected (5k paper subset): ~5000 papers, ~1000+ methods, ~200+ tasks, ~400+ datasets, ~10k+ relationships.
