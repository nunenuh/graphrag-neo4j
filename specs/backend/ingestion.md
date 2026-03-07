# Backend Spec: Ingestion Pipeline

File: `backend/src/graphrag_service/modules/graph/services.py` (`GraphService.ingest_nodes`, `GraphService.ingest_relationships`)

See also: [[projects/graphrag-neo4j/specs/backend/graph]] · [[projects/graphrag-neo4j/specs/backend/rag]]

---

## Responsibility

`GraphService` **orchestrates** the full ingestion pipeline:

```
PwC JSON files
    -> GraphService static iterators   (parse raw JSON -> entity dicts)
    -> EmbedderService.embed_batch()   (batch embed via OpenAI, from modules/rag/services.py)
    -> NodeRepository.upsert_batch()   (MERGE nodes + SET embedding)
    -> NodeRepository.merge_*()        (create relationships)
```

Parsing and ingestion live in the same `GraphService` class. Embedding is delegated to `EmbedderService` from `modules/rag/services.py`.

---

## Pipeline Phases

### Phase 1: Ingest Nodes (`GraphService.ingest_nodes`)

Iterates over all four entity types, embeds in batches, and upserts to Neo4j.

```python
def ingest_nodes(self, embed_batch_fn) -> None:
    """Ingest all entity types into Neo4j with embeddings."""
    settings = get_settings()
    batch_size = settings.INGEST_BATCH_SIZE

    for model, iter_name in NODE_MODEL_ITERATORS:
        iterator = getattr(self, iter_name)
        batch: list[dict] = []
        for node in tqdm(iterator(), desc=model.__label__):
            batch.append(node)
            if len(batch) == batch_size:
                texts = [
                    f"{n.get('title', n.get('name', ''))} "
                    f"{n.get('abstract', n.get('description', ''))}"
                    for n in batch
                ]
                embeddings = embed_batch_fn(texts)
                self.node_repo.upsert_batch(model, batch, embeddings)
                batch = []
        if batch:
            texts = [
                f"{n.get('title', n.get('name', ''))} "
                f"{n.get('abstract', n.get('description', ''))}"
                for n in batch
            ]
            embeddings = embed_batch_fn(texts)
            self.node_repo.upsert_batch(model, batch, embeddings)
```

The `embed_batch_fn` argument is `EmbedderService.embed_batch` from `modules/rag/services.py`.

**Model iterator mapping:**

| Model | Iterator | Source file |
|-------|----------|-------------|
| `Paper` | `iter_papers()` | `papers.json` |
| `Method` | `iter_methods()` | `methods.json` |
| `Task` | `iter_tasks()` | `tasks.json` |
| `Dataset` | `iter_datasets()` | `datasets.json` |

**Embedding text per entity type:**

| Entity | Text to embed |
|--------|--------------|
| `:Paper` | `f"{title} {abstract}"` |
| `:Method` | `f"{name} {description}"` |
| `:Task` | `f"{name} {description}"` |
| `:Dataset` | `f"{name} {description}"` |

### Phase 2: Ingest Relationships (`GraphService.ingest_relationships`)

Relationships are loaded from `evaluations.json` in the PwC archive format: `task -> datasets -> sota -> rows`.

```python
def ingest_relationships(self) -> None:
    """Load relationships from evaluation tables (pwc-archive format)."""
    eval_path = self._data_dir() / "evaluations.json"
    with open(eval_path) as f:
        evals = json.load(f)

    for ev in tqdm(evals, desc="Relationships"):
        task_name = ev.get("task", "")
        if not task_name:
            continue

        for ds_entry in ev.get("datasets", []):
            dataset_name = ds_entry.get("dataset", "")
            if not dataset_name:
                continue

            self.node_repo.merge_used_for(dataset_name, task_name)

            for row in (ds_entry.get("sota", {}).get("rows", []))[:5]:
                method_name = row.get("model_name", "")
                if not method_name:
                    continue
                metrics = row.get("metrics", {})
                for metric_name, metric_value in metrics.items():
                    self.node_repo.merge_evaluated_on(
                        method_name=method_name,
                        dataset_name=dataset_name,
                        metric=metric_name,
                        score=str(metric_value),
                    )
```

**PwC archive `evaluations.json` format:**

```json
[
  {
    "task": "Image Classification",
    "datasets": [
      {
        "dataset": "ImageNet",
        "sota": {
          "rows": [
            {
              "model_name": "ViT-H/14",
              "metrics": {
                "Top 1 Accuracy": "88.55",
                "Top 5 Accuracy": "98.64"
              }
            }
          ]
        }
      }
    ]
  }
]
```

**Relationship types created:**

| Relationship | Method | From -> To |
|-------------|--------|-----------|
| `USED_FOR` | `NodeRepository.merge_used_for()` | `:Dataset` -> `:Task` |
| `EVALUATED_ON` | `NodeRepository.merge_evaluated_on()` | `:Method` -> `:Dataset` (with `metric`, `score` properties) |

---

## Batch Upsert (`NodeRepository.upsert_batch`)

Handles batch MERGE with dynamic Cypher generation from neomodel model definitions.

```python
def upsert_batch(
    self,
    model: type[StructuredNode],
    nodes: list[dict],
    embeddings: list[list[float]],
) -> None:
    """Batch upsert nodes with embeddings using raw Cypher MERGE."""
    records = [{**node, "embedding": emb} for node, emb in zip(nodes, embeddings)]
    cypher = _get_upsert_cypher(model)
    self._client.run_query(cypher, {"rows": records})
```

The Cypher template is built dynamically by introspecting the neomodel class properties:

```python
def _get_upsert_cypher(model: type[StructuredNode]) -> str:
    label = model.__label__
    props = [k for k, v in model.defined_properties(aliases=False, rels=False).items()]
    set_parts = [f"n.{p} = row.{p}" for p in props]
    set_parts.append("n.embedding = row.embedding")
    set_clause = ", ".join(set_parts)
    return (
        f"UNWIND $rows AS row "
        f"MERGE (n:{label} {{uid: row.uid}}) "
        f"SET {set_clause}"
    )
```

---

## CLI

```bash
poetry run cli graph ingest
```

---

## Batching Rules

**Batch size:**
- Configurable via `INGEST_BATCH_SIZE` env var (default 50)
- Each batch is embedded and upserted as a single operation
- Uses `tqdm` for progress bars on all entity types and relationships

**OpenAI embedding API limits:**
- `EmbedderService.embed_batch()` handles internal batching at 100 texts per API call
- Retry/backoff logic handled in `EmbedderService`

**Neo4j write:**
- Uses `UNWIND $rows` for bulk writes — one Cypher call per batch
- Do NOT write one node per query (too slow for large datasets)

---

## Error Handling

| Error | Action |
|-------|--------|
| OpenAI `Exception` | Raises `OpenAIException` — stops ingestion |
| Neo4j write failure | Raises `RepositoryException` with label context |
| Missing required field | Skip record, continue (handled in iterator logic) |
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
