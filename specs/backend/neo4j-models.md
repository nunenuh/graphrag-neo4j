# Backend Spec: Neo4j Models & Database Layer (neomodel)

Files: `backend/src/graphrag_service/dbase/neo4j/`

---

## Overview

The database layer uses **neomodel v6** as an OGM (Object Graph Mapper) for Neo4j, similar to how SQLAlchemy works for relational databases. All node and relationship definitions live in `dbase/neo4j/models/`, and the client wrapper manages connection lifecycle.

```
dbase/neo4j/
├── __init__.py
├── client.py              # Connection wrapper over neomodel's db
└── models/
    ├── __init__.py         # Re-exports all models (required for neomodel registry)
    ├── base.py             # Abstract BaseNode + neomodel re-exports
    ├── nodes.py            # Concrete node models (Paper, Method, Task, Dataset)
    └── relationships.py    # StructuredRel definitions (UsedForRel, EvaluatedOnRel)
```

---

## Dependencies

```toml
# pyproject.toml
neo4j = "^5.19.0"
neomodel = "^6.1.0"
```

neomodel v6 requires Python 3.10+ and Neo4j 5.x.

---

## Connection Management (`client.py`)

Uses neomodel's built-in connection config instead of the raw neo4j driver.

```python
from neomodel import db, get_config, install_all_labels

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        host = uri.replace("bolt://", "").replace("neo4j://", "")
        config = get_config()
        config.database_url = f"bolt://{user}:{password}@{host}"

    def close(self) -> None:
        db.close_connection()

    def verify_connection(self) -> bool:
        db.cypher_query("RETURN 1")  # raises on failure

    def install_labels(self) -> None:
        install_all_labels()  # creates all constraints + indexes from models

    def run_query(self, cypher: str, params: dict | None = None) -> list:
        results, meta = db.cypher_query(cypher, params or {})
        return [dict(zip(meta, row)) for row in results] if meta else results
```

**Key differences from raw neo4j driver:**

| Feature | Raw neo4j driver | neomodel |
|---------|-----------------|----------|
| Connection | `GraphDatabase.driver(uri, auth=...)` | `get_config().database_url = ...` |
| Queries | `session.run(cypher, params)` returns Records | `db.cypher_query(cypher, params)` returns `(results, meta)` |
| Schema | Manual Cypher `CREATE CONSTRAINT ...` | `install_all_labels()` reads model definitions |
| Close | `driver.close()` | `db.close_connection()` |

**Lifecycle in FastAPI:**

- Startup: `Neo4jClient(uri, user, password)` — configures neomodel
- `install_labels()` — called via CLI `graph schema` command
- Shutdown: `client.close()` — calls `db.close_connection()`

---

## Abstract Base Node (`models/base.py`)

All node models inherit from `BaseNode`, which provides shared properties.

```python
from neomodel import DateTimeProperty, StringProperty, StructuredNode

class BaseNode(StructuredNode):
    __abstract_node__ = True

    uid = StringProperty(unique_index=True, required=True)
    created_at = DateTimeProperty(default_now=True)
```

**Design decisions:**

| Decision | Rationale |
|----------|-----------|
| `StringProperty(unique_index=True)` not `UniqueIdProperty()` | Our `uid` is a natural business key (paper URL, method ID from data source), not an auto-generated UUID |
| `__abstract_node__ = True` | Prevents neomodel from creating a `BaseNode` label in Neo4j |
| `created_at = DateTimeProperty(default_now=True)` | Automatic timestamp on node creation |

**Pitfall:** `required=True` and `default=...` cannot be combined in neomodel — it raises `ValueError`. `default_now=True` implicitly makes the field optional.

---

## Node Models (`models/nodes.py`)

Each model maps to a Neo4j node label with typed properties.

### Paper

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

### Method

```python
class Method(BaseNode):
    name = StringProperty(required=True, index=True)
    full_name = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(...)

    evaluated_on = RelationshipTo("Dataset", "EVALUATED_ON", model=EvaluatedOnRel)
```

### Task

```python
class Task(BaseNode):
    name = StringProperty(required=True, index=True)
    area = StringProperty()
    description = StringProperty()
    embedding = ArrayProperty(...)

    datasets = RelationshipFrom("Dataset", "USED_FOR", model=UsedForRel)
```

### Dataset

```python
class Dataset(BaseNode):
    name = StringProperty(required=True, index=True)
    description = StringProperty()
    modalities = StringProperty()
    embedding = ArrayProperty(...)

    used_for = RelationshipTo("Task", "USED_FOR", model=UsedForRel)
    evaluated_by = RelationshipFrom("Method", "EVALUATED_ON", model=EvaluatedOnRel)
```

### Model Registry

```python
ALL_NODE_MODELS: list[type[BaseNode]] = [Paper, Method, Task, Dataset]
```

Used by ingestion service to iterate over all entity types.

---

## Relationship Models (`models/relationships.py`)

Typed relationship properties using `StructuredRel`.

```python
from neomodel import StringProperty, StructuredRel

class UsedForRel(StructuredRel):
    """Dataset -[:USED_FOR]-> Task"""
    pass

class EvaluatedOnRel(StructuredRel):
    """Method -[:EVALUATED_ON]-> Dataset"""
    metric = StringProperty()
    score = StringProperty()
```

**Rules for relationships:**

- Define `StructuredRel` subclasses in `relationships.py`
- Attach `RelationshipTo` / `RelationshipFrom` on the node models in `nodes.py`
- Use string references (`"Dataset"` not `Dataset`) for forward references to avoid circular imports
- Do NOT create complementary `RelationshipTo` + `RelationshipFrom` pairs for bidirectional relationships — use a single `Relationship` instead (neomodel docs recommendation). Exception: when you need to traverse from both sides, define both (as we do for Dataset ↔ Task)

---

## Vector Indexes

neomodel v6 natively supports vector indexes via `VectorIndex` on `ArrayProperty`.

```python
from neomodel import ArrayProperty, FloatProperty
from neomodel.properties import VectorIndex

embedding = ArrayProperty(
    base_property=FloatProperty(),
    vector_index=VectorIndex(dimensions=1536, similarity_function="cosine"),
)
```

**Created in Neo4j by:** `install_all_labels()` — generates index name automatically as `vector_index_{Label}_{property}`.

**Queried via neomodel's `VectorFilter`:**

```python
from neomodel.semantic_filters import VectorFilter

results = Paper.nodes.filter(
    vector_filter=VectorFilter(
        topk=10,
        vector_attribute_name="embedding",
        candidate_vector=[0.1, 0.2, ...],
    )
).all()
# Returns list of (node, score) tuples
```

This replaces raw `CALL db.index.vector.queryNodes(...)` Cypher.

---

## Schema Installation

All constraints, uniqueness indexes, range indexes, and vector indexes are created by neomodel from model definitions:

```bash
# Via CLI
poetry run cli graph schema

# Programmatically
client.install_labels()  # calls neomodel.install_all_labels()
```

This replaces manual Cypher constraint/index creation. neomodel reads:
- `unique_index=True` → `CREATE CONSTRAINT ... IS UNIQUE`
- `index=True` → `CREATE INDEX ...` (RANGE index)
- `vector_index=VectorIndex(...)` → `CREATE VECTOR INDEX ...`

**Important:** You MUST call `install_all_labels()` before querying. Without it, constraints and vector indexes do not exist in Neo4j and `unique_index=True` has no effect.

---

## Property Reference

| neomodel Property | Python Type | Neo4j Type | Notes |
|-------------------|-------------|------------|-------|
| `StringProperty` | `str` | `String` | Use `required=True` for non-null, `unique_index=True` for unique constraint, `index=True` for range index |
| `IntegerProperty` | `int` | `Integer` | |
| `FloatProperty` | `float` | `Float` | |
| `BooleanProperty` | `bool` | `Boolean` | |
| `DateTimeProperty` | `datetime` | `DateTime` | `default_now=True` for auto-timestamp |
| `ArrayProperty` | `list` | `List` | Requires `base_property=` parameter |
| `UniqueIdProperty` | `str` | `String` | Auto-generates `uuid4().hex`, sets `unique_index=True`. Use only when you need a surrogate key |

**Property parameter reference:**

| Parameter | Effect |
|-----------|--------|
| `required=True` | Value must be provided on creation (cannot combine with `default=`) |
| `unique_index=True` | Creates a uniqueness constraint (via `install_all_labels()`) |
| `index=True` | Creates a RANGE index for faster lookups |
| `default=value` | Default value (or callable) |
| `default_now=True` | DateTimeProperty-only: defaults to current UTC time |
| `db_property="name"` | Use a different property name in Neo4j |
| `choices={"A", "B"}` | Restrict allowed values |

---

## Common Pitfalls

1. **Forgetting `install_all_labels()`** — constraints and indexes only exist after calling it. Without it, `unique_index=True` does nothing in Neo4j.

2. **Property names starting with `_`** — reserved for neomodel internals, silently ignored.

3. **`create_or_update` with `UniqueIdProperty`** — always creates new nodes (each call generates new UUID). Use `merge_by={"keys": ["uid"]}` to merge on business key.

4. **Long indexed strings** — Neo4j truncates indexed strings at 4039 bytes. Two strings differing only after that mark will collide.

5. **Hot-reload conflicts** — neomodel raises `NodeClassAlreadyDefined` if a model class is re-imported. Set `get_config().allow_reload = True` in development.

6. **All model files must be imported** — neomodel builds its class registry at import time. The `models/__init__.py` must import all models, or `resolve_objects=True` on queries will fail.

7. **`required=True` + `default=...`** — raises `ValueError`. Choose one.

---

## How Repositories Use Models

Repositories live in each module (`modules/graph/repositories.py`, `modules/rag/repositories.py`) and encapsulate all Neo4j queries.

**For batch ingestion** (raw Cypher for performance):

```python
def _get_upsert_cypher(model: type[StructuredNode]) -> str:
    props = list(model.defined_properties(aliases=False, rels=False).keys())
    set_parts = [f"n.{p} = row.{p}" for p in props]
    set_parts.append("n.embedding = row.embedding")
    return f"UNWIND $rows AS row MERGE (n:{model.__label__} {{uid: row.uid}}) SET {', '.join(set_parts)}"
```

**For vector search** (neomodel OGM):

```python
hits = Paper.nodes.filter(
    vector_filter=VectorFilter(topk=k, vector_attribute_name="embedding", candidate_vector=vec)
).all()
```

**For graph traversal** (raw Cypher — neomodel OGM doesn't support multi-hop):

```python
client.run_query(TRAVERSE_QUERY, {"ids": node_ids})
```

**Rule:** Use neomodel OGM for simple queries (find by property, vector search). Use raw Cypher via `client.run_query()` for batch operations, multi-hop traversals, and aggregations.

---

## `__init__.py` — Model Registry

All models must be imported in `models/__init__.py` so neomodel discovers them:

```python
from .base import BaseNode
from .nodes import ALL_NODE_MODELS, Dataset, Method, Paper, Task
from .relationships import EvaluatedOnRel, UsedForRel
```

This is not optional — neomodel uses import-time registration.
