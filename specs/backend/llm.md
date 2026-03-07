# Backend Spec: LLM Integration (LangChain / LangGraph)

Files: `backend/src/graphrag_service/library/llm/`, `backend/src/graphrag_service/library/graph/`

See also: [rag.md](rag.md) · [graph.md](graph.md) · [python-module-structure](../conventions/python-module-structure.md)

---

## Design Goal

Provider-agnostic LLM and embedding support via **LangChain**. The system must support OpenAI, Google Gemini, Qwen, Ollama, and any future provider by changing config — not code.

Workflow orchestration (RAG pipeline, multi-step reasoning) uses **LangGraph** for stateful, graph-based execution.

---

## Library Structure

LLM and workflow logic live in `library/` because they are **reusable building blocks** — they use frameworks (LangChain, LangGraph) but are not tied to specific modules or DB models.

```
library/
├── __init__.py
├── parsers.py              # JSON data parsing (existing)
├── llm/                    # LangChain-based LLM abstraction
│   ├── __init__.py         # Re-exports: get_chat_model, get_embeddings, generate
│   ├── providers.py        # Provider factory functions
│   ├── chat.py             # Chat model wrapper (invoke, generate with prompt)
│   └── embeddings.py       # Embedding model wrapper (embed_text, embed_batch)
└── graph/                  # LangGraph workflow definitions
    ├── __init__.py         # Re-exports: run_rag_pipeline
    └── rag_pipeline.py     # RAG pipeline as a LangGraph StateGraph
```

---

## Configuration

New environment variables for provider-agnostic LLM support:

```bash
# LLM Provider
LLM_PROVIDER=openai            # openai | google | ollama | qwen
LLM_MODEL=gpt-4o-mini          # Model name for the chosen provider

# Embedding Provider
EMBEDDING_PROVIDER=openai      # openai | google | ollama | qwen
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Provider API Keys (set only the ones you use)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

### `core/config.py` additions

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # LLM
    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL: str = Field(default="gpt-4o-mini")

    # Embeddings
    EMBEDDING_PROVIDER: str = Field(default="openai")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIM: int = Field(default=1536)

    # Provider keys
    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")

    # Ollama
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
```

---

## `library/llm/providers.py` — Provider Factory

Creates LangChain model instances based on config. This is the **only place** that knows about provider-specific classes.

```python
"""
Provider factory — returns LangChain model instances based on config.
"""
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import get_settings


def get_chat_model() -> BaseChatModel:
    """Create a chat model instance based on LLM_PROVIDER config."""
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()
    model = settings.LLM_MODEL

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=settings.OPENAI_API_KEY, temperature=0.2)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=settings.GOOGLE_API_KEY)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, base_url=settings.OLLAMA_BASE_URL)

    if provider == "qwen":
        from langchain_openai import ChatOpenAI
        # Qwen uses OpenAI-compatible API
        return ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def get_embeddings() -> Embeddings:
    """Create an embeddings instance based on EMBEDDING_PROVIDER config."""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()
    model = settings.EMBEDDING_MODEL

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            dimensions=settings.EMBEDDING_DIM,
        )

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=settings.GOOGLE_API_KEY,
        )

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=model, base_url=settings.OLLAMA_BASE_URL)

    raise ValueError(f"Unsupported embedding provider: {provider}")
```

**Rules:**
- Lazy imports — provider packages are only imported when selected
- If a provider is not installed, the import fails at runtime with a clear error
- Config is read via `get_settings()`, never hardcoded
- New providers are added by adding an `if` branch here — no changes elsewhere

---

## `library/llm/embeddings.py` — Embedding Wrapper

Wraps LangChain embeddings with batch support and error handling.

```python
"""
Embedding wrapper — provides embed_text and embed_batch using LangChain embeddings.
"""
from graphrag_service.core.logging import get_logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_embeddings

logger = get_logger(__name__)


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns zero vector for empty input."""
    if not text or not text.strip():
        from graphrag_service.core.config import get_settings
        return [0.0] * get_settings().EMBEDDING_DIM

    try:
        embeddings = get_embeddings()
        return embeddings.embed_query(text.replace("\n", " "))
    except Exception as e:
        raise ServiceException(f"Embedding failed: {e}")


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed a list of texts in batches. Returns embeddings in input order."""
    embeddings_model = get_embeddings()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ") if t else "" for t in texts[i : i + batch_size]]
        try:
            batch_embeddings = embeddings_model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            raise ServiceException(f"Batch embedding failed at batch {i}: {e}")

    return all_embeddings
```

**Key points:**
- `embed_query()` for single text (query-time)
- `embed_documents()` for batch (ingestion-time)
- Empty strings produce zero vectors
- Raises `ServiceException` on failure (not provider-specific exceptions)

---

## `library/llm/chat.py` — Chat Model Wrapper

Wraps LangChain chat models for answer generation.

```python
"""
Chat model wrapper — provides generate function using LangChain chat models.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from graphrag_service.core.logging import get_logger
from graphrag_service.shared.exceptions import ServiceException

from .providers import get_chat_model

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a helpful assistant answering questions about ML research.
You receive structured context from a knowledge graph (Papers, Methods, Tasks, Datasets).
Use ONLY the provided context. Cite specific entities. If context is insufficient, say so."""


def generate(question: str, context: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Generate an answer given a question and context string."""
    try:
        chat = get_chat_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
        ]
        response = chat.invoke(messages)
        return str(response.content)
    except Exception as e:
        raise ServiceException(f"LLM generation failed: {e}")
```

---

## `library/llm/__init__.py` — Re-exports

```python
"""LangChain-based LLM abstraction — provider-agnostic chat and embeddings."""

from .chat import SYSTEM_PROMPT, generate
from .embeddings import embed_batch, embed_text
from .providers import get_chat_model, get_embeddings

__all__ = [
    "get_chat_model",
    "get_embeddings",
    "embed_text",
    "embed_batch",
    "generate",
    "SYSTEM_PROMPT",
]
```

---

## `library/graph/rag_pipeline.py` — LangGraph RAG Workflow

The RAG pipeline is modeled as a **LangGraph StateGraph** for composability, observability, and future extensibility (multi-step reasoning, tool use, etc.).

```python
"""
RAG pipeline as a LangGraph StateGraph.
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph

from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)


class RAGState(TypedDict):
    """State flowing through the RAG pipeline."""
    question: str
    query_vector: list[float]
    seed_nodes: list[dict]
    subgraph: dict          # {nodes, edges, cypher_used}
    context: str
    answer: str


def build_rag_graph(
    embed_fn,
    search_fn,
    traverse_fn,
    build_context_fn,
    generate_fn,
) -> StateGraph:
    """Build the RAG pipeline graph.

    Each function argument is injected by the caller (usecase layer),
    keeping this graph definition free of DB or provider dependencies.

    Args:
        embed_fn: (question: str) -> list[float]
        search_fn: (vector: list[float]) -> list[dict]
        traverse_fn: (node_ids: list[str]) -> dict
        build_context_fn: (seed_nodes, edges) -> str
        generate_fn: (question: str, context: str) -> str
    """
    def embed_step(state: RAGState) -> dict:
        vector = embed_fn(state["question"])
        return {"query_vector": vector}

    def search_step(state: RAGState) -> dict:
        seeds = search_fn(state["query_vector"])
        return {"seed_nodes": seeds}

    def traverse_step(state: RAGState) -> dict:
        ids = [s["id"] for s in state["seed_nodes"]]
        subgraph = traverse_fn(ids)
        return {"subgraph": subgraph}

    def context_step(state: RAGState) -> dict:
        context = build_context_fn(
            state["seed_nodes"],
            state["subgraph"].get("edges", []),
        )
        return {"context": context}

    def generate_step(state: RAGState) -> dict:
        answer = generate_fn(state["question"], state["context"])
        return {"answer": answer}

    graph = StateGraph(RAGState)
    graph.add_node("embed", embed_step)
    graph.add_node("search", search_step)
    graph.add_node("traverse", traverse_step)
    graph.add_node("context", context_step)
    graph.add_node("generate", generate_step)

    graph.set_entry_point("embed")
    graph.add_edge("embed", "search")
    graph.add_edge("search", "traverse")
    graph.add_edge("traverse", "context")
    graph.add_edge("context", "generate")
    graph.add_edge("generate", END)

    return graph


def run_rag_pipeline(
    question: str,
    embed_fn,
    search_fn,
    traverse_fn,
    build_context_fn,
    generate_fn,
) -> RAGState:
    """Build and run the RAG pipeline, returning the final state."""
    graph = build_rag_graph(embed_fn, search_fn, traverse_fn, build_context_fn, generate_fn)
    app = graph.compile()
    result = app.invoke({"question": question})
    return result
```

**Design decisions:**
- Functions are **injected** — the graph definition has no imports from modules, DB, or providers
- The usecase layer wires repository methods and library functions into the graph
- `RAGState` is a TypedDict for type safety and LangGraph compatibility
- Pipeline is linear now but can be extended with branching, retry, or tool-use nodes
- Each step returns a partial state update (LangGraph merges it)

---

## `library/graph/__init__.py` — Re-exports

```python
"""LangGraph workflow definitions."""

from .rag_pipeline import RAGState, build_rag_graph, run_rag_pipeline

__all__ = ["RAGState", "build_rag_graph", "run_rag_pipeline"]
```

---

## How Modules Use the Library

### RAG Module (`modules/rag/`)

The RAG module's **service** orchestrates library calls, and the **usecase** wires everything together with repositories.

```python
# modules/rag/services.py — orchestrates library calls (NO DB access)
from graphrag_service.library.llm import embed_text, embed_batch, generate
from graphrag_service.library.llm.chat import SYSTEM_PROMPT


class RAGService:
    """Orchestrates LLM library calls for the RAG pipeline."""

    def embed_question(self, question: str) -> list[float]:
        return embed_text(question)

    def generate_answer(self, question: str, context: str) -> str:
        return generate(question, context)

    def build_context(self, seed_nodes: list, edges: list) -> str:
        # Uses library/generator.py build_context (existing)
        from graphrag_service.library.generator import build_context
        return build_context(seed_nodes, edges)
```

```python
# modules/rag/usecase.py — orchestrates service + repository
from graphrag_service.library.graph import run_rag_pipeline

from .repositories import VectorSearchRepository, TraversalRepository
from .services import RAGService


class RAGUseCase:
    """Orchestrates the full RAG pipeline via LangGraph."""

    def __init__(self, client):
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

### Graph Module (`modules/graph/`)

The graph module uses `library/llm/embeddings.py` for ingestion embeddings:

```python
# modules/graph/services.py — uses library for parsing + embedding
from graphrag_service.library.llm import embed_batch
from graphrag_service.library.parsers import iter_papers, load_json


class GraphService:
    """Orchestrates library calls for data parsing and embedding."""

    def embed_nodes(self, texts: list[str]) -> list[list[float]]:
        return embed_batch(texts)
```

---

## Dependencies (`pyproject.toml`)

```toml
[tool.poetry.dependencies]
# LangChain core
langchain-core = "^0.3"
langgraph = "^0.3"

# Provider packages (install only what you use)
langchain-openai = "^0.3"           # OpenAI (default)
langchain-google-genai = "^2.1"     # Google Gemini (optional)
langchain-ollama = "^0.3"           # Ollama local (optional)
```

**Rules:**
- `langchain-core` and `langgraph` are always required
- Provider packages are optional — install only the ones you need
- The `openai` direct dependency can be removed once LangChain handles all LLM calls
- Keep `neomodel` for DB operations — LangChain is for LLM only, not for Neo4j queries

---

## Migration Path

The current codebase uses `openai` SDK directly. The migration to LangChain/LangGraph:

| Current | After Migration |
|---------|----------------|
| `openai.OpenAI(api_key=...)` in `EmbedderService` | `library/llm/embeddings.py` via LangChain |
| `openai.OpenAI(api_key=...)` in `GeneratorService` | `library/llm/chat.py` via LangChain |
| `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `LLM_MODEL` | Add `LLM_PROVIDER`, `EMBEDDING_PROVIDER` |
| Sequential RAG in `RAGService.query()` | `library/graph/rag_pipeline.py` via LangGraph |
| `EmbedderService` in `modules/rag/` | `library/llm/embeddings.py` (shared) |
| `GeneratorService` in `modules/rag/` | `library/llm/chat.py` (shared) |

**Backwards compatible**: Existing `OPENAI_API_KEY` + `LLM_MODEL` still work — defaults are `LLM_PROVIDER=openai`.
