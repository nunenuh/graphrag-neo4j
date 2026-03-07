# Backend Spec: RAG Pipeline

Files: `backend/src/graphrag_service/modules/rag/` (services, repositories, usecase)

LLM abstraction: `backend/src/graphrag_service/library/llm/` (LangChain)

Workflow: `backend/src/graphrag_service/library/graph/rag_pipeline.py` (LangGraph)

See also: [llm.md](llm.md) · [graph.md](graph.md)

---

## Pipeline Overview (LangGraph)

The RAG pipeline is modeled as a **LangGraph StateGraph** with 5 steps:

```
question: str
    |
    v  [embed]     library.llm.embed_text (LangChain embeddings)
query_vector: list[float]
    |
    v  [search]    VectorSearchRepository.search_all (neomodel VectorFilter)
seed_nodes: list[dict]
    |
    v  [traverse]  TraversalRepository.traverse (raw Cypher 2-hop)
subgraph: dict  {nodes, edges, cypher_used}
    |
    v  [context]   library.generator.build_context (text serialization)
context: str
    |
    v  [generate]  library.llm.generate (LangChain chat model)
answer: str
    |
    v  RAGUseCase.query (orchestration via LangGraph)
tuple[str, dict]
```

The pipeline graph is defined in `library/graph/rag_pipeline.py` and wired by `modules/rag/usecase.py`. See [llm.md](llm.md) for details.

---

## Dataclasses

Defined in `services.py`:

```python
@dataclass
class SeedNode:
    id: str
    label: str
    name: str
    score: float
    properties: dict = field(default_factory=dict)

    @classmethod
    def from_search_result(cls, result: VectorSearchResult) -> "SeedNode": ...


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
```

Defined in `repositories.py`:

```python
@dataclass(frozen=True)
class VectorSearchResult:
    id: str
    label: str
    name: str
    score: float
    properties: dict = field(default_factory=dict)
```

---

## Imports and Dependencies

### Services (business logic — uses library only)

```python
from graphrag_service.core.config import get_settings
from graphrag_service.core.logging import get_logger
from graphrag_service.library.llm import embed_text, embed_batch, generate
from graphrag_service.library.generator import build_context
```

### Repositories (DB operations only)

```python
from neomodel import StructuredNode
from neomodel.semantic_filters import VectorFilter
from graphrag_service.dbase.neo4j.client import Neo4jClient
from graphrag_service.dbase.neo4j.models import Paper, Method, Task, Dataset
from graphrag_service.shared.exceptions import RepositoryException
```

### UseCase (orchestration — wires service + repository via LangGraph)

```python
from graphrag_service.library.graph import run_rag_pipeline
from .services import RAGService
from .repositories import VectorSearchRepository, TraversalRepository
```

Configuration values (model names, dimensions, top_k) come from `get_settings()` -- never hardcoded.

---

## Embedding (via LangChain)

Embeddings are now in `library/llm/embeddings.py` — provider-agnostic via LangChain. See [llm.md](llm.md) for full details.

```python
from graphrag_service.library.llm import embed_text, embed_batch
```

**Rules:**
- `embed_text` for query-time (single text, interactive) — uses `embed_query()`
- `embed_batch` for ingestion (bulk, chunked by `batch_size`) — uses `embed_documents()`
- Never call `embed_text` in a loop -- use `embed_batch`
- Newlines are replaced with spaces; empty strings produce a zero vector
- Raises `ServiceException` on any failure (not provider-specific exceptions)
- Provider and model come from `EMBEDDING_PROVIDER` + `EMBEDDING_MODEL` config

---

## `VectorSearchRepository`

Uses neomodel `VectorFilter` for similarity search. Lives in `repositories.py`.

```python
SEARCH_MODELS: list[type[StructuredNode]] = [Paper, Method, Task, Dataset]

class VectorSearchRepository:

    def __init__(self, client: Neo4jClient):
        self._client = client

    def search(self, vec: list[float], model: type[StructuredNode], k: int) -> list[VectorSearchResult]:
        """Search a single neomodel node class by vector similarity."""
        hits = model.nodes.filter(
            vector_filter=VectorFilter(
                topk=k,
                vector_attribute_name="embedding",
                candidate_vector=vec,
            )
        ).all()
        ...

    def search_all(self, vec: list[float], k: int) -> list[VectorSearchResult]:
        """Search across all 4 node models and return top-k overall."""
        ...
```

**Key details:**
- Vector search uses `neomodel.semantic_filters.VectorFilter` -- not raw `CALL db.index.vector.queryNodes` Cypher
- Searches all 4 model types: `Paper`, `Method`, `Task`, `Dataset`
- Results from all models are merged, sorted by score descending, and truncated to top-k
- Node ID is `node.uid` (not `node.id`)
- Embedding property is excluded from the returned `properties` dict
- Raises `RepositoryException` on failure

---

## `TraversalRepository`

Raw Cypher for 2-hop traversal. Lives in `repositories.py`. Neomodel does not support multi-hop traversal natively, so this uses the Neo4j client directly.

```python
TRAVERSE_QUERY = """
    MATCH (seed) WHERE seed.uid IN $ids
    OPTIONAL MATCH (seed)-[r1]->(n1)
    OPTIONAL MATCH (n1)-[r2]->(n2)
    RETURN seed,
           collect(DISTINCT {from: seed.uid, to: n1.uid, type: type(r1), props: properties(r1)}) AS e1,
           collect(DISTINCT n1) AS nodes1,
           collect(DISTINCT {from: n1.uid,  to: n2.uid, type: type(r2), props: properties(r2)}) AS e2,
           collect(DISTINCT n2) AS nodes2
"""

class TraversalRepository:

    def __init__(self, client: Neo4jClient):
        self._client = client

    def traverse(self, node_ids: list[str]) -> tuple[dict[str, dict], list[dict]]:
        """Perform 2-hop traversal from seed node IDs.
        Returns (nodes_by_id, edges_list)."""
        ...
```

**Key details:**
- Uses `seed.uid` (not `seed.id`) in all Cypher
- Embedding properties are stripped from returned node dicts
- Null nodes from `OPTIONAL MATCH` are filtered out
- Edges require non-null `from`, `to`, and `type` to be included
- Raises `RepositoryException` on failure

---

## `RAGService` (Service Layer)

Orchestrates library calls — NO DB access. Lives in `modules/rag/services.py`.

```python
class RAGService:
    """Orchestrates LLM library calls for the RAG pipeline."""

    def embed_question(self, question: str) -> list[float]:
        """Embed a question using library/llm."""
        return embed_text(question)

    def generate_answer(self, question: str, context: str) -> str:
        """Generate an answer using library/llm."""
        return generate(question, context)

    def build_context(self, seed_nodes: list, edges: list) -> str:
        """Build context string using library/generator."""
        return build_context(seed_nodes, edges)
```

**Rules:**
- Service uses `library/llm` and `library/generator` — never DB or repositories
- Provider and model are transparent — configured via `LLM_PROVIDER` / `EMBEDDING_PROVIDER`
- Raises `ServiceException` on failure

---

## LLM Generation (via LangChain)

Generation is now in `library/llm/chat.py` — provider-agnostic via LangChain. See [llm.md](llm.md) for full details.

```python
from graphrag_service.library.llm import generate
```

**Rules:**
- LLM model comes from `LLM_PROVIDER` + `LLM_MODEL` config
- System prompt instructs the LLM to answer ONLY from the provided context
- Edges in context are capped at 30 to avoid overwhelming the prompt
- Raises `ServiceException` on failure (not provider-specific exceptions)

---

## Context Serialization Format

The `_build_context` method produces structured text (not prose):

```
=== GRAPH CONTEXT ===
SEED NODES:
  [Method] YOLO (score=0.92)
  [Task] Object Detection (score=0.91)

RELATIONSHIPS:
  (yolo-uid) -[APPLIED_ON]-> (coco-uid) {...}
  (paper-uid) -[INTRODUCES]-> (yolo-uid) {...}
```

Design rationale:
1. **Structured, not prose** -- LLMs parse structured formats more reliably
2. **Entity-centric** -- label and score shown for each seed node
3. **Relationship-explicit** -- `(from) -[TYPE]-> (to)` format with optional properties

---

## `RAGUseCase` (UseCase Layer)

Orchestrates the full pipeline via LangGraph. Lives in `modules/rag/usecase.py`.

```python
from graphrag_service.library.graph import run_rag_pipeline

from .repositories import VectorSearchRepository, TraversalRepository
from .services import RAGService


class RAGUseCase:
    """Orchestrates the full RAG pipeline — wires service + repository into LangGraph."""

    def __init__(self, client: Neo4jClient):
        self.service = RAGService()
        self.vector_repo = VectorSearchRepository(client)
        self.traversal_repo = TraversalRepository(client)

    def query(self, question: str) -> tuple[str, dict]:
        """Run the RAG pipeline using LangGraph."""
        result = run_rag_pipeline(
            question=question,
            embed_fn=self.service.embed_question,
            search_fn=self.vector_repo.search_all,
            traverse_fn=self.traversal_repo.traverse,
            build_context_fn=self.service.build_context,
            generate_fn=self.service.generate_answer,
        )
        return result["answer"], result["subgraph"]
```

**Key points:**
- UseCase wires service (library calls) + repository (DB) into LangGraph
- The LangGraph pipeline handles the execution flow (embed → search → traverse → context → generate)
- Each step function is injected — the graph definition has no direct dependencies
- See [llm.md](llm.md) for the full LangGraph pipeline definition

---

## Example Questions (used in UI)

These 4 examples are pre-seeded in the frontend:

1. `"What methods are used for object detection?"`
2. `"Which papers introduced transformer architectures?"`
3. `"What datasets are used to benchmark image classification?"`
4. `"How does BERT relate to other NLP methods?"`

These questions should produce well-connected subgraphs with the 5k PwC subset.
