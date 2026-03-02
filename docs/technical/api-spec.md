# API Specification — graphrag-neo4j

**Base URL:** `http://localhost:8000`
**Version:** v1.0
**Format:** JSON

---

## Endpoints

### POST /api/query

Main Graph RAG pipeline. Accepts a natural language question and returns a grounded answer with the retrieved subgraph.

**Request**
```json
{
  "question": "What methods are used for object detection?"
}
```

**Response 200**
```json
{
  "answer": "The most prominent methods for object detection include YOLO (You Only Look Once) and its variants, which are applied on COCO and Pascal VOC datasets...",
  "seed_nodes": [
    {
      "id": "yolo",
      "label": "Method",
      "name": "YOLO",
      "score": 0.924
    },
    {
      "id": "object-detection",
      "label": "Task",
      "name": "Object Detection",
      "score": 0.911
    }
  ],
  "nodes": [
    { "id": "yolo", "name": "YOLO", "label": "Method", "description": "..." },
    { "id": "coco", "name": "COCO", "label": "Dataset", "description": "..." }
  ],
  "edges": [
    {
      "from_id": "yolo",
      "to_id": "coco",
      "type": "APPLIED_ON",
      "properties": {}
    },
    {
      "from_id": "yolo",
      "to_id": "coco",
      "type": "EVALUATED_ON",
      "properties": { "metric": "mAP", "score": "45.5" }
    }
  ],
  "cypher_used": "MATCH (seed) WHERE seed.id IN $ids\nOPTIONAL MATCH (seed)-[r1]->(n1)...",
  "latency_ms": 2340
}
```

**Error 400**
```json
{ "detail": "Question cannot be empty" }
```

**Error 500**
```json
{ "detail": "Internal server error" }
```

---

### GET /api/graph/schema

Returns all available node labels and relationship types in the graph.

**Response 200**
```json
{
  "node_labels": ["Paper", "Method", "Task", "Dataset"],
  "relationship_types": ["INTRODUCES", "APPLIED_ON", "EVALUATED_ON", "USED_FOR", "VARIANT_OF", "SUBTASK_OF"]
}
```

---

### GET /api/graph/explore

Returns a sample of the graph for initial visualization before a query is made.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max number of relationships to return |

**Response 200**
```json
{
  "nodes": [
    { "id": "yolo", "name": "YOLO", "label": "Method" },
    { "id": "coco", "name": "COCO", "label": "Dataset" }
  ],
  "edges": [
    { "from": "yolo", "to": "coco", "type": "APPLIED_ON" }
  ]
}
```

---

### GET /api/health

System health check. Returns status of the API and Neo4j connection.

**Response 200**
```json
{
  "status": "ok",
  "neo4j": "connected",
  "version": "0.1.0"
}
```

**Response 200 (degraded)**
```json
{
  "status": "ok",
  "neo4j": "error",
  "version": "0.1.0"
}
```

---

## Data Models

### QueryRequest
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Natural language question |

### SeedNode
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Node ID in Neo4j |
| `label` | string | Node type: Paper / Method / Task / Dataset |
| `name` | string | Human-readable name |
| `score` | float | Cosine similarity score (0–1) |

### GraphNode
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Node ID |
| `label` | string | Node type |
| `name` | string | Name (for Method/Task/Dataset) |
| `title` | string | Title (for Paper nodes) |
| `description` | string | Optional description |

### GraphEdge
| Field | Type | Description |
|-------|------|-------------|
| `from_id` | string | Source node ID |
| `to_id` | string | Target node ID |
| `type` | string | Relationship type |
| `properties` | object | Edge properties (e.g. `{metric, score}` for EVALUATED_ON) |

### QueryResponse
| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | LLM-generated answer |
| `seed_nodes` | SeedNode[] | Nodes found by vector search |
| `nodes` | GraphNode[] | All nodes in retrieved subgraph |
| `edges` | GraphEdge[] | All edges in retrieved subgraph |
| `cypher_used` | string | The Cypher query executed |
| `latency_ms` | integer | Total response time in milliseconds |

---

## CORS

Backend allows requests from `http://localhost:5173` (Vite dev server) and `http://localhost:3000` (production preview).
In production, configure `ALLOWED_ORIGINS` environment variable.
