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
├── parsers.py              # JSON data parsing
├── generator.py            # Context serialization (build_context)
├── llm/                    # LangChain-based LLM abstraction
│   ├── __init__.py         # Re-exports: get_chat_model, get_embeddings, generate
│   ├── chat.py             # Chat model wrapper (generate with prompt)
│   ├── embeddings.py       # Embedding wrapper (embed_text, embed_batch)
│   └── providers/          # Provider registry — one module per provider
│       ├── __init__.py     # Re-exports: get_chat_model, get_embeddings
│       ├── registry.py     # Provider dispatch (resolves name → module)
│       ├── openai.py       # OpenAI (ChatOpenAI, OpenAIEmbeddings)
│       ├── google.py       # Google Gemini (ChatGoogleGenerativeAI)
│       ├── ollama.py       # Ollama local (ChatOllama, OllamaEmbeddings)
│       └── qwen.py         # Qwen via OpenAI-compatible API
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

## `library/llm/providers/` — Provider Registry Package

Each provider lives in its own module. A registry dispatches to the correct module based on config. This is the **only place** that knows about provider-specific classes.

### Adding a New Provider

1. Create `providers/<name>.py` with `get_chat_model(settings)` and `get_embeddings(settings)`
2. Register it in `registry.py`'s `_PROVIDERS` dict
3. No changes needed elsewhere

### `providers/registry.py` — Dispatch

```python
"""
Provider registry — resolves provider name to module and creates model instances.
"""
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings, get_settings

from . import google, ollama, openai, qwen

_PROVIDERS: dict[str, object] = {
    "openai": openai,
    "google": google,
    "ollama": ollama,
    "qwen": qwen,
}


def get_chat_model() -> BaseChatModel:
    """Create a chat model instance based on LLM_PROVIDER config."""
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()
    module = _PROVIDERS.get(provider)
    if module is None:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Available: {', '.join(_PROVIDERS)}"
        )
    return module.get_chat_model(settings)


def get_embeddings() -> Embeddings:
    """Create an embeddings instance based on EMBEDDING_PROVIDER config."""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()
    module = _PROVIDERS.get(provider)
    if module is None:
        raise ValueError(
            f"Unsupported embedding provider: '{provider}'. "
            f"Available: {', '.join(_PROVIDERS)}"
        )
    return module.get_embeddings(settings)
```

### `providers/openai.py` — Example Provider Module

```python
"""OpenAI provider — ChatOpenAI and OpenAIEmbeddings."""
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_service.core.config import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)


def get_embeddings(settings: Settings) -> Embeddings:
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
        dimensions=settings.EMBEDDING_DIM,
    )
```

Other provider modules follow the same pattern: `google.py`, `ollama.py`, `qwen.py`. Each receives the full `Settings` object and can use provider-specific fields (e.g., `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`).

### `providers/__init__.py` — Re-exports

```python
from .registry import get_chat_model, get_embeddings

__all__ = ["get_chat_model", "get_embeddings"]
```

**Rules:**
- Lazy imports — provider SDK packages are only imported inside the provider module when selected
- If a provider package is not installed, the import fails at runtime with a clear error
- Config is read via `get_settings()` in the registry, then passed to each provider module
- Each provider module receives `Settings` and can customize model creation with provider-specific settings
- New providers require only a new module file + one dict entry in the registry

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
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from graphrag_service.core.logging import get_logger

logger = get_logger(__name__)


class RAGState(TypedDict):
    """State flowing through the RAG pipeline."""
    question: str
    query_vector: list[float]
    seed_nodes: list[dict]
    subgraph: dict          # {seed_nodes, nodes, edges, cypher_used}
    context: str
    answer: str


def build_rag_graph(
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
) -> StateGraph:
    """Build the RAG pipeline graph.

    Each function argument is injected by the caller (usecase layer),
    keeping this graph definition free of DB or provider dependencies.
    """
    def embed_step(state: RAGState) -> dict:
        vector = embed_fn(state["question"])
        return {"query_vector": vector}

    def search_step(state: RAGState) -> dict:
        results = search_fn(state["query_vector"], top_k)
        seeds = [
            {
                "id": r.id, "label": r.label, "name": r.name,
                "score": r.score, "properties": r.properties,
            }
            for r in results
        ]
        return {"seed_nodes": seeds}

    def traverse_step(state: RAGState) -> dict:
        ids = [s["id"] for s in state["seed_nodes"]]
        nodes_dict, edges_list = traverse_fn(ids)
        return {
            "subgraph": {
                "seed_nodes": state["seed_nodes"],
                "nodes": list(nodes_dict.values()),
                "edges": edges_list,
                "cypher_used": "neomodel VectorFilter + 2-hop traversal",
            }
        }

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
    embed_fn: Callable[[str], list[float]],
    search_fn: Callable[[list[float], int], list[Any]],
    traverse_fn: Callable[[list[str]], tuple[dict, list]],
    build_context_fn: Callable[[list, list], str],
    generate_fn: Callable[[str, str], str],
    top_k: int = 5,
) -> RAGState:
    """Build and run the RAG pipeline, returning the final state."""
    graph = build_rag_graph(
        embed_fn, search_fn, traverse_fn, build_context_fn, generate_fn, top_k
    )
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

The RAG module's **service** orchestrates library calls (static methods, no state), and the **usecase** wires everything together with repositories via LangGraph.

```python
# modules/rag/services.py — orchestrates library calls (NO DB access)
from graphrag_service.library.generator import build_context
from graphrag_service.library.llm import embed_text, generate


class RAGService:
    """Orchestrates LLM library calls for the RAG pipeline. No DB access."""

    @staticmethod
    def embed_question(question: str) -> list[float]:
        return embed_text(question)

    @staticmethod
    def generate_answer(question: str, context: str) -> str:
        return generate(question, context)

    @staticmethod
    def build_context(seed_nodes: list, edges: list) -> str:
        return build_context(seed_nodes, edges)
```

```python
# modules/rag/usecase.py — orchestrates service + repository
from graphrag_service.core.config import get_settings
from graphrag_service.library.graph import run_rag_pipeline

from .repositories import VectorSearchRepository, TraversalRepository
from .services import RAGService


class RAGUseCase:
    """Orchestrates the full RAG pipeline — wires service + repository into LangGraph."""

    def __init__(self, client: Neo4jClient):
        self.service = RAGService()
        self.vector_repo = VectorSearchRepository(client)
        self.traversal_repo = TraversalRepository(client)

    def query(self, question: str) -> dict:
        """Run the RAG pipeline using LangGraph.

        Returns the full pipeline state dict with keys:
            question, query_vector, seed_nodes, subgraph, context, answer
        """
        settings = get_settings()
        result = run_rag_pipeline(
            question=question,
            embed_fn=self.service.embed_question,
            search_fn=self.vector_repo.search_all,
            traverse_fn=self.traversal_repo.traverse,
            build_context_fn=self.service.build_context,
            generate_fn=self.service.generate_answer,
            top_k=settings.TOP_K_SEED_NODES,
        )
        return result
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

Managed via `poetry add` — never edit `pyproject.toml` directly.

```toml
[tool.poetry.dependencies]
# AI / ML (LangChain provider-agnostic)
langchain-core = "^1.2.17"
langgraph = "^1.0.10"
langchain-openai = "^1.1.10"       # OpenAI (default provider)

# Optional provider packages (install only what you use)
# langchain-google-genai = "^2.1"  # Google Gemini
# langchain-ollama = "^0.3"        # Ollama local
```

**Rules:**
- `langchain-core` and `langgraph` are always required
- `langchain-openai` is installed by default (default provider)
- Other provider packages are optional — install only the ones you need
- The direct `openai` SDK dependency has been removed — LangChain handles all LLM calls
- Keep `neomodel` for DB operations — LangChain is for LLM only, not for Neo4j queries
- **Backwards compatible**: Existing `OPENAI_API_KEY` + `LLM_MODEL` still work — defaults are `LLM_PROVIDER=openai`
