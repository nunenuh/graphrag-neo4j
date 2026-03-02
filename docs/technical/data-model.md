# Data Model — graphrag-neo4j

**Date:** 2026-03-02
**Database:** Neo4j 5.15

---

## Graph Schema

### Node Types

#### :Paper
Represents a research paper from Papers With Code.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Paper URL (unique identifier) |
| `title` | string | Full paper title |
| `abstract` | string | Abstract text (capped at 2000 chars) |
| `year` | string | Publication year (YYYY) |
| `url` | string | Direct URL to paper |
| `embedding` | float[] | 1536-dim vector (text-embedding-3-small) |

**Embedded text:** `title + " " + abstract`

---

#### :Method
Represents an ML algorithm or architectural component.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Method ID or name (unique) |
| `name` | string | Short name (e.g. "YOLO") |
| `full_name` | string | Full name (e.g. "You Only Look Once") |
| `description` | string | Method description (capped at 2000 chars) |
| `embedding` | float[] | 1536-dim vector |

**Embedded text:** `name + " " + description`

---

#### :Task
Represents an ML task category.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Task ID or name (unique) |
| `name` | string | Task name (e.g. "Object Detection") |
| `area` | string | Broad area (e.g. "Computer Vision") |
| `description` | string | Task description (capped at 1000 chars) |
| `embedding` | float[] | 1536-dim vector |

**Embedded text:** `name + " " + description`

---

#### :Dataset
Represents a benchmark dataset.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Dataset ID or name (unique) |
| `name` | string | Dataset name (e.g. "COCO") |
| `description` | string | Dataset description (capped at 1000 chars) |
| `modalities` | string | Comma-separated modalities (e.g. "Images, Texts") |
| `embedding` | float[] | 1536-dim vector |

**Embedded text:** `name + " " + description`

---

### Relationship Types

| Relationship | From | To | Properties | Description |
|-------------|------|-----|------------|-------------|
| `INTRODUCES` | :Paper | :Method | — | Paper proposes this method |
| `ADDRESSES` | :Paper | :Task | — | Paper works on this task |
| `APPLIED_ON` | :Method | :Dataset | — | Method is used with this dataset |
| `EVALUATED_ON` | :Method | :Dataset | `metric`, `score` | Method is benchmarked on this dataset |
| `USED_FOR` | :Dataset | :Task | — | Dataset is used to benchmark this task |
| `VARIANT_OF` | :Method | :Method | — | Method is a variant of another |
| `SUBTASK_OF` | :Task | :Task | — | Task is a subtask of another |

---

### Vector Indexes

| Index Name | Node Type | Property | Dimensions | Similarity |
|-----------|-----------|----------|------------|------------|
| `paper_embeddings` | :Paper | `embedding` | 1536 | cosine |
| `method_embeddings` | :Method | `embedding` | 1536 | cosine |
| `task_embeddings` | :Task | `embedding` | 1536 | cosine |
| `dataset_embeddings` | :Dataset | `embedding` | 1536 | cosine |

---

### Uniqueness Constraints

```cypher
CREATE CONSTRAINT paper_id   FOR (p:Paper)   REQUIRE p.id IS UNIQUE
CREATE CONSTRAINT method_id  FOR (m:Method)  REQUIRE m.id IS UNIQUE
CREATE CONSTRAINT task_id    FOR (t:Task)    REQUIRE t.id IS UNIQUE
CREATE CONSTRAINT dataset_id FOR (d:Dataset) REQUIRE d.id IS UNIQUE
```

---

## Data Source Mapping

### Papers With Code → Neo4j

| PwC File | PwC Field | → Neo4j Node | Property |
|----------|-----------|-------------|----------|
| `papers.json` | `paper_url` | :Paper | `id` |
| `papers.json` | `title` | :Paper | `title` |
| `papers.json` | `abstract` | :Paper | `abstract` |
| `papers.json` | `published` | :Paper | `year` |
| `methods.json` | `name` | :Method | `name`, `id` |
| `methods.json` | `full_name` | :Method | `full_name` |
| `methods.json` | `description` | :Method | `description` |
| `tasks.json` | `name` | :Task | `name`, `id` |
| `tasks.json` | `area` | :Task | `area` |
| `datasets.json` | `name` | :Dataset | `name`, `id` |
| `datasets.json` | `modalities` | :Dataset | `modalities` |
| `evaluations.json` | `task.task_name` | :Task | node created if missing |
| `evaluations.json` | `dataset.dataset_name` | → USED_FOR | relationship |
| `evaluations.json` | `sota_rows[].method_name` | → EVALUATED_ON | relationship |
| `evaluations.json` | `sota_rows[].metrics` | EVALUATED_ON | `{metric, score}` |

---

## Scale (v1 MVP)

| Entity | Count |
|--------|-------|
| :Paper | ~5,000 |
| :Method | ~1,000–2,000 |
| :Task | ~500–1,000 |
| :Dataset | ~500–1,000 |
| Total nodes | ~7,000–9,000 |
| Relationships | ~15,000–30,000 |

Total embedding vectors: ~9,000 × 1536 floats ≈ ~55 MB in Neo4j
