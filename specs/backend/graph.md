# Backend Spec: Graph Layer

Files: `backend/src/graphrag_service/modules/graph/services.py`, `backend/src/graphrag_service/modules/graph/repositories.py`

See also: [[projects/graphrag-neo4j/docs/technical/data-model]]

---

## Responsibility

| File | Does |
|------|------|
| `modules/graph/services.py` | `GraphService` class — schema management, data parsing (static iterators), ingestion orchestration, graph exploration |
| `modules/graph/repositories.py` | `SchemaRepository`, `NodeRepository`, `GraphExploreRepository` — encapsulate all Neo4j Cypher queries |

The graph layer **never** embeds — that is `EmbedderService.embed_batch()` from `modules/rag/services.py`.

---

## Node Models (neomodel)

Node models are defined in `dbase/neo4j/models/nodes.py` using neomodel. All models extend `BaseNode` (from `dbase/neo4j/models/base.py`), which provides:

```python
class BaseNode(StructuredNode):
    __abstract_node__ = True
    uid = StringProperty(unique_index=True, required=True)
    created_at = DateTimeProperty(default_now=True)
```

### `:Paper`
```python
class Paper(BaseNode):
    title = StringProperty(required=True)
    abstract = StringProperty()
    year = StringProperty()
    url = StringProperty()
    embedding = ArrayProperty(
        base_property=FloatProperty(),
        vector_index=VectorIndex(dimensions=1536, similarity_function="cosine"),
    )
```

### `:Method`
```python
class Method(BaseNode):
    name = StringProperty(required=True, index=True)
    full_name = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(
        base_property=FloatProperty(),
        vector_index=VectorIndex(dimensions=1536, similarity_function="cosine"),
    )
    evaluated_on = RelationshipTo("Dataset", "EVALUATED_ON", model=EvaluatedOnRel)
```

### `:Task`
```python
class Task(BaseNode):
    name = StringProperty(required=True, index=True)
    area = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(
        base_property=FloatProperty(),
        vector_index=VectorIndex(dimensions=1536, similarity_function="cosine"),
    )
    datasets = RelationshipFrom("Dataset", "USED_FOR", model=UsedForRel)
```

### `:Dataset`
```python
class Dataset(BaseNode):
    name = StringProperty(required=True, index=True)
    description = StringProperty()
    modalities = StringProperty()
    embedding = ArrayProperty(
        base_property=FloatProperty(),
        vector_index=VectorIndex(dimensions=1536, similarity_function="cosine"),
    )
    used_for = RelationshipTo("Task", "USED_FOR", model=UsedForRel)
    evaluated_by = RelationshipFrom("Method", "EVALUATED_ON", model=EvaluatedOnRel)
```

---

## Relationships

Relationship models are defined in `dbase/neo4j/models/relationships.py` using neomodel `StructuredRel`.

| Relationship | From -> To | Model | Properties |
|-------------|-----------|-------|------------|
| `USED_FOR` | `:Dataset` -> `:Task` | `UsedForRel` | none |
| `EVALUATED_ON` | `:Method` -> `:Dataset` | `EvaluatedOnRel` | `metric: str`, `score: str` |

```python
class UsedForRel(StructuredRel):
    """Dataset -[:USED_FOR]-> Task relationship."""
    pass

class EvaluatedOnRel(StructuredRel):
    """Method -[:EVALUATED_ON]-> Dataset relationship with metric properties."""
    metric = StringProperty()
    score = StringProperty()
```

---

## Schema Management

Schema is managed by neomodel. Calling `install_all_labels()` creates constraints and indexes automatically from model definitions (unique indexes on `uid`, secondary indexes on `name`, vector indexes on `embedding`).

### `SchemaRepository`

```python
class SchemaRepository:
    def install_schema(self) -> None:
        """Install all constraints and indexes via neomodel's install_all_labels."""
        self._client.install_labels()

    def get_labels(self) -> List[str]: ...
    def get_relationship_types(self) -> List[str]: ...
    def get_schema(self) -> Tuple[List[str], List[str]]: ...
```

### CLI

```bash
poetry run cli graph schema
```

**Rules:**
- Safe to re-run — neomodel uses `IF NOT EXISTS` semantics
- Vector dimension is always 1536 (`text-embedding-3-small`)
- Similarity function is always `cosine`
- No hand-written Cypher for constraints or indexes — neomodel derives them from model definitions

---

## Data Parsing — Static Methods on `GraphService`

Parsing is done as static methods on `GraphService` in `modules/graph/services.py`. Each method returns an `Iterator[dict]` for memory efficiency.

### `iter_papers()`

```python
@staticmethod
def iter_papers() -> Iterator[dict]:
    for p in GraphService._load("papers.json")[:settings.MAX_PAPERS]:
        if not p.get("title") or not p.get("abstract"):
            continue
        yield {
            "uid": p.get("paper_url", p.get("id", "")),
            "title": p["title"].strip(),
            "abstract": p["abstract"].strip()[:2000],
            "year": p.get("published", "")[:4],
            "url": p.get("paper_url", ""),
        }
```

### `iter_methods()`

```python
@staticmethod
def iter_methods() -> Iterator[dict]:
    for m in GraphService._load("methods.json"):
        if not m.get("name"):
            continue
        yield {
            "uid": m.get("id", m["name"]),
            "name": m["name"].strip(),
            "full_name": m.get("full_name", m["name"]).strip(),
            "description": (m.get("description") or "")[:2000],
        }
```

### `iter_tasks()`

```python
@staticmethod
def iter_tasks() -> Iterator[dict]:
    for t in GraphService._load("tasks.json"):
        if not t.get("name"):
            continue
        yield {
            "uid": t.get("id", t["name"]),
            "name": t["name"].strip(),
            "area": t.get("area", "").strip(),
            "description": (t.get("description") or "")[:1000],
        }
```

### `iter_datasets()`

```python
@staticmethod
def iter_datasets() -> Iterator[dict]:
    for d in GraphService._load("datasets.json"):
        if not d.get("name"):
            continue
        yield {
            "uid": d.get("id", d["name"]),
            "name": d["name"].strip(),
            "description": (d.get("description") or "")[:1000],
            "modalities": ", ".join(d.get("modalities", [])),
        }
```

**Parser Rules:**
- Always return new dicts — never mutate the raw input
- Use generator pattern (`Iterator[dict]`) — memory-efficient for large datasets
- Missing optional fields default to empty string, never `None`
- IDs use the `uid` field with natural business keys from the data source (not slugified)
- Skip records with missing required fields (title/abstract for papers, name for others)
- Descriptions are truncated to 1000-2000 characters to keep embeddings focused

---

## ID Generation Rules

| Entity | `uid` Rule | Example |
|--------|-----------|---------|
| Paper | `paper_url` field from source, fallback to `id` | `"https://arxiv.org/abs/1706.03762"` |
| Method | `id` field from source, fallback to `name` | `"transformer"` |
| Task | `id` field from source, fallback to `name` | `"image-classification"` |
| Dataset | `id` field from source, fallback to `name` | `"imagenet"` |

IDs are natural business keys from the PwC data source. No slugification is applied.

---

## Repository Classes

### `NodeRepository`

Handles batch upsert and relationship MERGE queries.

```python
class NodeRepository:
    def upsert_batch(self, model: type[StructuredNode], nodes: list[dict], embeddings: list[list[float]]) -> None: ...
    def merge_used_for(self, dataset_name: str, task_name: str) -> None: ...
    def merge_evaluated_on(self, method_name: str, dataset_name: str, metric: str, score: str) -> None: ...
```

Upsert Cypher is dynamically generated from neomodel model definitions:

```python
def _get_upsert_cypher(model: type[StructuredNode]) -> str:
    """Build and cache the UNWIND/MERGE Cypher for a neomodel class."""
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

### `GraphExploreRepository`

Returns a subgraph sample for visualization.

```python
class GraphExploreRepository:
    def explore(self, limit: int = 50) -> Tuple[list, list]: ...
```

---

## Cypher Query Patterns

### MERGE (upsert) — always use MERGE, never CREATE

```cypher
UNWIND $rows AS row
MERGE (n:Paper {uid: row.uid})
SET n.title = row.title,
    n.abstract = row.abstract,
    n.url = row.url,
    n.year = row.year,
    n.embedding = row.embedding
```

### Create relationship (USED_FOR)

```cypher
MATCH (d:Dataset {name: $dname})
MATCH (t:Task {name: $tname})
MERGE (d)-[:USED_FOR]->(t)
```

### Create relationship (EVALUATED_ON with properties)

```cypher
MATCH (m:Method {name: $mname})
MATCH (d:Dataset {name: $dname})
MERGE (m)-[r:EVALUATED_ON {metric: $metric}]->(d)
SET r.score = $score
```

**Rules:**
- Always `MERGE`, never `CREATE` for nodes (idempotent)
- `MERGE` on relationships after `MATCH`ing both endpoints
- Set properties with `SET` after MERGE (don't put them in the MERGE pattern unless they are identity)
- Parameterize all values — never string-interpolate into Cypher
