# Backend Spec: RAG Pipeline

Files: `backend/src/library/rag/embedder.py`, `backend/src/library/rag/retriever.py`, `backend/src/library/rag/generator.py`

See also: [[projects/graphrag-neo4j/docs/technical/architecture]] · [[projects/graphrag-neo4j/docs/technical/data-model]]

---

## Pipeline Overview

```
question: str
    │
    ▼ embedder.py
query_vector: list[float]  (1536 dims)
    │
    ▼ retriever.py — vector search
seed_nodes: list[SeedNode]  (top-k by cosine similarity)
    │
    ▼ retriever.py — graph traversal
subgraph: {nodes: [...], edges: [...]}
    │
    ▼ generator.py — context serialization
context_text: str  ("YOLO -[APPLIED_ON]-> COCO...")
    │
    ▼ generator.py — LLM call
answer: str  (grounded natural language)
    │
    ▼ router.py — response assembly
QueryResponse (answer + seed_nodes + nodes + edges + cypher_used + latency_ms)
```

---

## `library/rag/embedder.py`

```python
"""
library/rag/embedder.py

OpenAI text embedding — single text and batch.
Model: text-embedding-3-small (1536 dimensions)
"""
import logging
import time
from typing import Union

import openai

from core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds, doubles each retry


def embed_text(text: str) -> list[float]:
    """
    Embed a single text string.

    Args:
        text: Text to embed (will be truncated to 8191 tokens by OpenAI)

    Returns:
        List of 1536 floats (cosine-normalized)

    Raises:
        openai.APIError: If the API call fails after retries
    """
    client = openai.OpenAI(api_key=settings.openai_api_key)
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                input=[text],
                model=EMBEDDING_MODEL,
            )
            return response.data[0].embedding
        except openai.RateLimitError:
            wait = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Rate limited. Waiting {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    raise openai.RateLimitError("Max retries exceeded")


def batch_embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts in batches of BATCH_SIZE.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings, same length and order as input

    Raises:
        openai.APIError: If any batch fails after retries
    """
    client = openai.OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"Embedding batch {batch_num}/{total_batches} ({len(batch)} texts)")

        for attempt in range(MAX_RETRIES):
            try:
                response = client.embeddings.create(
                    input=batch,
                    model=EMBEDDING_MODEL,
                )
                # Preserve order — API returns in order, but be explicit
                batch_embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
                embeddings.extend(batch_embeddings)
                break
            except openai.RateLimitError:
                wait = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Rate limited on batch {batch_num}. Waiting {wait}s")
                time.sleep(wait)
            except openai.APIError as e:
                logger.error(f"OpenAI API error on batch {batch_num}: {e}")
                raise

    return embeddings
```

**Rules:**
- `embed_text` for query-time (single text, interactive)
- `batch_embed` for ingestion (bulk, respects rate limits)
- Never call `embed_text` in a loop — use `batch_embed`
- Always retry on `RateLimitError`, never on `AuthenticationError`
- Return order must match input order

---

## `library/rag/retriever.py`

```python
"""
library/rag/retriever.py

Vector search → seed nodes → graph traversal → subgraph.
"""
import logging
from dataclasses import dataclass

from dbase.neo4j.client import Neo4jClient
from library.rag.embedder import embed_text

logger = logging.getLogger(__name__)

TOP_K = 5           # seed nodes per entity type
TRAVERSAL_DEPTH = 2 # hops from seed nodes


@dataclass
class SeedNode:
    id: str
    label: str
    name: str
    score: float


@dataclass
class GraphNode:
    id: str
    label: str
    name: str
    title: str = ""
    description: str = ""


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    type: str
    properties: dict


@dataclass
class Subgraph:
    seed_nodes: list[SeedNode]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    cypher_used: str


def retrieve(question: str, client: Neo4jClient) -> Subgraph:
    """
    Run the full retrieval pipeline for a question.

    1. Embed the question
    2. Vector search across all 4 entity types
    3. Collect unique seed nodes
    4. Graph traversal from seed nodes (depth 1-2)
    5. Return subgraph

    Args:
        question: Natural language question
        client: Neo4j client

    Returns:
        Subgraph with seed_nodes, nodes, edges, cypher_used
    """
    # Step 1: Embed query
    query_vector = embed_text(question)

    # Step 2: Vector search
    seed_nodes = _vector_search(client, query_vector)
    seed_ids = [node.id for node in seed_nodes]

    # Step 3: Graph traversal
    nodes, edges, traversal_cypher = _graph_traversal(client, seed_ids)

    return Subgraph(
        seed_nodes=seed_nodes,
        nodes=nodes,
        edges=edges,
        cypher_used=traversal_cypher,
    )


def _vector_search(client: Neo4jClient, query_vector: list[float]) -> list[SeedNode]:
    """Search all vector indexes and return deduplicated top-k seed nodes."""
    seed_nodes: dict[str, SeedNode] = {}  # id → SeedNode (dedup by id)

    searches = [
        ("method_embeddings", "Method"),
        ("task_embeddings", "Task"),
        ("paper_embeddings", "Paper"),
        ("dataset_embeddings", "Dataset"),
    ]

    for index_name, label in searches:
        cypher = f"""
        CALL db.index.vector.queryNodes($index_name, $top_k, $query_vector)
        YIELD node, score
        RETURN node.id AS id, '{label}' AS label,
               coalesce(node.name, node.title, node.id) AS name,
               score
        ORDER BY score DESC
        """
        results = client.run_query(cypher, {
            "index_name": index_name,
            "top_k": TOP_K,
            "query_vector": query_vector,
        })
        for row in results:
            node_id = row["id"]
            if node_id not in seed_nodes:
                seed_nodes[node_id] = SeedNode(
                    id=node_id,
                    label=row["label"],
                    name=row["name"],
                    score=row["score"],
                )

    return list(seed_nodes.values())


def _graph_traversal(
    client: Neo4jClient,
    seed_ids: list[str],
) -> tuple[list[GraphNode], list[GraphEdge], str]:
    """
    Traverse the graph from seed nodes up to depth 2.

    Returns nodes, edges, and the Cypher query used.
    """
    cypher = """
    MATCH (seed)
    WHERE seed.id IN $seed_ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    WITH
        collect(DISTINCT seed) + collect(DISTINCT n1) + collect(DISTINCT n2) AS all_nodes,
        collect(DISTINCT r1) + collect(DISTINCT r2) AS all_rels
    UNWIND all_nodes AS node
    WITH DISTINCT node, all_rels
    WHERE node IS NOT NULL
    RETURN
        node.id AS id,
        labels(node)[0] AS label,
        coalesce(node.name, '') AS name,
        coalesce(node.title, '') AS title,
        coalesce(node.description, '') AS description,
        all_rels
    """

    results = client.run_query(cypher, {"seed_ids": seed_ids})

    nodes = []
    edges_seen: set[str] = set()
    edges = []

    all_rels = results[0]["all_rels"] if results else []

    for row in results:
        nodes.append(GraphNode(
            id=row["id"],
            label=row["label"],
            name=row["name"],
            title=row["title"],
            description=row["description"],
        ))

    for rel in all_rels:
        if rel is None:
            continue
        edge_key = f"{rel.start_node['id']}-{rel.type}-{rel.end_node['id']}"
        if edge_key not in edges_seen:
            edges_seen.add(edge_key)
            edges.append(GraphEdge(
                from_id=rel.start_node["id"],
                to_id=rel.end_node["id"],
                type=rel.type,
                properties=dict(rel),
            ))

    return nodes, edges, cypher
```

**Retriever Rules:**
- Dedup seed nodes across entity types (same ID can come up in multiple searches)
- Graph traversal depth is configurable — start at 2 (depth 1 + depth 2)
- Never embed inside `retrieve()` directly — call `embed_text()` from `embedder.py`
- `cypher_used` must be the actual traversal Cypher (sent to frontend for display)
- Handle empty results gracefully — `OPTIONAL MATCH` means some results may be None

---

## `library/rag/generator.py`

```python
"""
library/rag/generator.py

Context serialization + LLM answer generation.
"""
import logging

import openai

from core.config import settings
from library.rag.retriever import GraphEdge, GraphNode, SeedNode

logger = logging.getLogger(__name__)

LLM_MODEL = "gpt-4o-mini"
MAX_TOKENS = 1024
TEMPERATURE = 0.1  # Low temperature — we want grounded, factual answers

SYSTEM_PROMPT = """You are a knowledgeable assistant for ML research.
You answer questions about machine learning methods, tasks, papers, and datasets.
Base your answers ONLY on the provided graph context.
Be specific and cite methods, papers, or datasets from the context.
If the context does not contain enough information, say so honestly."""


def serialize_context(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    seed_nodes: list[SeedNode],
) -> str:
    """
    Serialize a subgraph into a structured text context for the LLM.

    Format:
        SEED NODES (most relevant):
        - YOLO (Method, score: 0.924)

        GRAPH RELATIONSHIPS:
        - YOLO -[APPLIED_ON]-> COCO
        - Paper: "You Only Look Once" -[INTRODUCES]-> YOLO

    Args:
        nodes: All nodes in the subgraph
        edges: All edges in the subgraph
        seed_nodes: Vector search results (scored)

    Returns:
        Structured text context string
    """
    lines = ["SEED NODES (most relevant to your question):"]
    for sn in seed_nodes[:5]:  # Cap at 5 for context brevity
        lines.append(f"- {sn.name} ({sn.label}, similarity: {sn.score:.3f})")

    lines.append("")
    lines.append("GRAPH RELATIONSHIPS:")

    node_map = {n.id: n for n in nodes}

    for edge in edges:
        src = node_map.get(edge.from_id)
        dst = node_map.get(edge.to_id)
        if not src or not dst:
            continue

        src_name = src.title or src.name or src.id
        dst_name = dst.title or dst.name or dst.id

        if edge.properties:
            props = ", ".join(f"{k}={v}" for k, v in edge.properties.items() if v)
            rel_str = f"-[{edge.type} {{{props}}}]->"
        else:
            rel_str = f"-[{edge.type}]->"

        lines.append(f"- {src_name} {rel_str} {dst_name}")

    return "\n".join(lines)


def generate_answer(
    question: str,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    seed_nodes: list[SeedNode],
) -> str:
    """
    Generate a grounded answer using GPT-4o-mini.

    Args:
        question: User's natural language question
        nodes: Subgraph nodes
        edges: Subgraph edges
        seed_nodes: Vector search results

    Returns:
        Natural language answer grounded in the subgraph

    Raises:
        openai.APIError: If LLM call fails
    """
    context = serialize_context(nodes, edges, seed_nodes)
    client = openai.OpenAI(api_key=settings.openai_api_key)

    user_message = f"""Context from the ML Knowledge Graph:
{context}

Question: {question}"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content or ""
    logger.info(f"Generated answer ({len(answer)} chars), tokens used: {response.usage.total_tokens}")
    return answer
```

**Generator Rules:**
- `TEMPERATURE = 0.1` — low, for factual grounded answers
- System prompt must state "answer ONLY from the provided context"
- Cap seed nodes in context at 5 — more adds noise, not signal
- Always return empty string on None (never raise from missing content)
- Log token usage for cost monitoring

---

## Context Serialization Format

The context passed to the LLM must be:
1. **Structured, not prose** — the LLM reads it better
2. **Entity-centric** — name the node, state its type and score
3. **Relationship-explicit** — `A -[REL {props}]-> B` format

Example output:
```
SEED NODES (most relevant to your question):
- YOLO (Method, similarity: 0.924)
- Object Detection (Task, similarity: 0.911)

GRAPH RELATIONSHIPS:
- YOLO -[APPLIED_ON]-> COCO
- YOLO -[EVALUATED_ON {metric=mAP, score=45.5}]-> COCO
- You Only Look Once -[INTRODUCES]-> YOLO
- You Only Look Once -[ADDRESSES]-> Object Detection
```

---

## Example Questions (used in UI)

These 4 examples are pre-seeded in the frontend:

1. `"What methods are used for object detection?"`
2. `"Which papers introduced transformer architectures?"`
3. `"What datasets are used to benchmark image classification?"`
4. `"How does BERT relate to other NLP methods?"`

These questions should produce well-connected subgraphs with the 5k PwC subset.
