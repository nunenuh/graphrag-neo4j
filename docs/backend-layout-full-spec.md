# Backend Project Layout — Full Spec Implementation

**Date**: 2026-03-08
**Reference**: [comparison-with-full-spec.md](comparison-with-full-spec.md)

This document shows what the backend layout looks like with all full-spec features implemented. Files marked with `[NEW]` don't exist yet. Existing files are marked `[EXISTS]`.

---

## Layout

```
backend/src/graphrag_service/
├── __init__.py                                    [EXISTS]
├── main.py                                        [EXISTS]  App factory, CORS, lifespan
├── router.py                                      [EXISTS]  Aggregates module routers under /api/v1/
│
├── core/                                          ─── Framework plumbing ───
│   ├── __init__.py                                [EXISTS]
│   ├── config.py                                  [EXISTS]  Pydantic Settings (+ new config fields)
│   ├── auth.py                                    [EXISTS]  X-API-Key dependency
│   ├── logging.py                                 [EXISTS]  structlog setup
│   └── dependencies.py                            [EXISTS]  Neo4j client singleton
│
├── dbase/                                         ─── Database layer ───
│   └── neo4j/
│       ├── __init__.py                            [EXISTS]
│       ├── client.py                              [EXISTS]  Neo4j client (neomodel)
│       └── models/
│           ├── __init__.py                        [EXISTS]  Re-exports all models
│           ├── base.py                            [EXISTS]  BaseNode (uid, created_at)
│           ├── nodes.py                           [EXISTS → EXTEND]  + Author, Organization, Result, Repository
│           └── relationships.py                   [EXISTS → EXTEND]  + AUTHORED, AFFILIATED_WITH, USES_METHOD, etc.
│
├── shared/                                        ─── Cross-module concerns ───
│   ├── __init__.py                                [EXISTS]
│   ├── exceptions.py                              [EXISTS]  Exception hierarchy
│   ├── utils/
│   │   ├── __init__.py                            [EXISTS]
│   │   └── text.py                                [NEW]  Text normalization (diacritics, CJK, whitespace)
│   ├── services/
│   │   └── __init__.py                            [EXISTS]
│   └── repositories/
│       └── __init__.py                            [EXISTS]
│
├── library/                                       ─── Reusable logic (no DB, no modules) ───
│   ├── __init__.py                                [EXISTS]
│   ├── parsers.py                                 [EXISTS]  PwC JSON parsing (iter_papers, etc.)
│   ├── generator.py                               [EXISTS → EXTEND]  Context builder (+ budget mgmt)
│   │
│   ├── llm/                                       ─── LangChain LLM abstraction ───
│   │   ├── __init__.py                            [EXISTS]  Re-exports
│   │   ├── chat.py                                [EXISTS]  generate()
│   │   ├── embeddings.py                          [EXISTS]  embed_text(), embed_batch()
│   │   ├── classifier.py                          [NEW]  LLM-based query type classifier
│   │   ├── extractor.py                           [NEW]  LLM-based entity extraction from text
│   │   ├── reranker.py                            [NEW]  LLM-based result reranking
│   │   └── providers/                             ─── One module per LLM provider ───
│   │       ├── __init__.py                        [EXISTS]
│   │       ├── registry.py                        [EXISTS]  Provider dispatch
│   │       ├── openai.py                          [EXISTS]
│   │       ├── google.py                          [EXISTS]
│   │       ├── ollama.py                          [EXISTS]
│   │       ├── qwen.py                            [EXISTS]
│   │       └── anthropic.py                       [NEW]  Claude provider
│   │
│   ├── graph/                                     ─── LangGraph workflow definitions ───
│   │   ├── __init__.py                            [EXISTS]  Re-exports
│   │   ├── rag_pipeline.py                        [EXISTS → EXTEND]  Linear pipeline (current)
│   │   └── agentic_pipeline.py                    [NEW]  Branching pipeline with query routing
│   │
│   ├── entity_resolution/                         [NEW] ─── Entity resolution library ───
│   │   ├── __init__.py                            [NEW]  Re-exports
│   │   ├── normalizer.py                          [NEW]  Name normalization (diacritics, CJK, initials)
│   │   ├── blocking.py                            [NEW]  Candidate generation (last_name + first_initial)
│   │   ├── scoring.py                             [NEW]  Similarity scoring (Jaro-Winkler, co-author, topic)
│   │   └── merger.py                              [NEW]  Auto-merge + human review queue
│   │
│   ├── analytics/                                 [NEW] ─── Graph analytics library ───
│   │   ├── __init__.py                            [NEW]  Re-exports
│   │   ├── community.py                           [NEW]  Leiden community detection (networkx fallback)
│   │   ├── centrality.py                          [NEW]  PageRank, betweenness, closeness
│   │   ├── trends.py                              [NEW]  Method/task trend scoring (time windows)
│   │   └── diffusion.py                           [NEW]  Method diffusion tracking across areas
│   │
│   └── retrieval/                                 [NEW] ─── Retrieval strategy library ───
│       ├── __init__.py                            [NEW]  Re-exports
│       ├── merger.py                              [NEW]  Reciprocal Rank Fusion (RRF)
│       └── context_budget.py                      [NEW]  Token-aware context assembly (40/40/20)
│
├── modules/                                       ─── Feature modules (Handler→UseCase→Service→Repo) ───
│   ├── __init__.py                                [EXISTS]
│   │
│   ├── health/                                    ─── Health checks ───
│   │   ├── __init__.py                            [EXISTS]
│   │   ├── schemas.py                             [EXISTS]
│   │   ├── services.py                            [EXISTS]
│   │   ├── usecase.py                             [EXISTS]
│   │   ├── apiv1/
│   │   │   ├── __init__.py                        [EXISTS]
│   │   │   └── handler.py                         [EXISTS]
│   │   └── cli/
│   │       ├── __init__.py                        [EXISTS]
│   │       └── commands.py                        [EXISTS]
│   │
│   ├── graph/                                     ─── Graph schema, ingestion, exploration ───
│   │   ├── __init__.py                            [EXISTS]
│   │   ├── schemas.py                             [EXISTS → EXTEND]  + author/org/result response models
│   │   ├── services.py                            [EXISTS → EXTEND]  + author/org parsing, enrichment
│   │   ├── repositories.py                        [EXISTS → EXTEND]  + author/org/result queries
│   │   ├── usecase.py                             [EXISTS → EXTEND]  + ER orchestration, analytics trigger
│   │   ├── apiv1/
│   │   │   ├── __init__.py                        [EXISTS]
│   │   │   └── handler.py                         [EXISTS → EXTEND]  + /authors, /orgs, /trends endpoints
│   │   └── cli/
│   │       ├── __init__.py                        [EXISTS]
│   │       └── commands.py                        [EXISTS → EXTEND]  + graph analytics, graph resolve
│   │
│   ├── rag/                                       ─── RAG pipeline ───
│   │   ├── __init__.py                            [EXISTS]
│   │   ├── schemas.py                             [EXISTS → EXTEND]  + citations, provenance fields
│   │   ├── services.py                            [EXISTS → EXTEND]  + query classification, reranking
│   │   ├── repositories.py                        [EXISTS → EXTEND]  + hybrid search, temporal queries
│   │   ├── usecase.py                             [EXISTS → EXTEND]  + agentic pipeline orchestration
│   │   ├── apiv1/
│   │   │   ├── __init__.py                        [EXISTS]
│   │   │   └── handler.py                         [EXISTS → EXTEND]  + provenance in response
│   │   └── cli/
│   │       ├── __init__.py                        [EXISTS]
│   │       └── commands.py                        [NEW]  CLI for testing RAG queries
│   │
│   ├── analytics/                                 [NEW] ─── Graph analytics module ───
│   │   ├── __init__.py                            [NEW]
│   │   ├── schemas.py                             [NEW]  CommunityOut, CentralityOut, TrendOut
│   │   ├── services.py                            [NEW]  Orchestrates library/analytics
│   │   ├── repositories.py                        [NEW]  Read/write community_id, pagerank, etc.
│   │   ├── usecase.py                             [NEW]  Run analytics, generate summaries
│   │   ├── apiv1/
│   │   │   ├── __init__.py                        [NEW]
│   │   │   └── handler.py                         [NEW]  /communities, /trends, /centrality
│   │   └── cli/
│   │       ├── __init__.py                        [NEW]
│   │       └── commands.py                        [NEW]  analytics run, analytics status
│   │
│   └── eval/                                      [NEW] ─── Evaluation module ───
│       ├── __init__.py                            [NEW]
│       ├── schemas.py                             [NEW]  EvalResult, MetricScore
│       ├── services.py                            [NEW]  LLM judge, provenance checker
│       ├── repositories.py                        [NEW]  Store eval results
│       ├── usecase.py                             [NEW]  Run eval suite, compare baselines
│       ├── queries.py                             [NEW]  40 test queries with gold answers
│       └── cli/
│           ├── __init__.py                        [NEW]
│           └── commands.py                        [NEW]  eval run, eval report, eval compare
│
└── cli/                                           ─── CLI entry point ───
    ├── __init__.py                                [EXISTS]
    ├── base.py                                    [EXISTS]  Rich console setup
    └── main.py                                    [EXISTS → EXTEND]  + register analytics, eval commands
```

---

## New Config Fields (`core/config.py`)

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Entity Resolution
    ER_AUTO_MERGE_THRESHOLD: float = Field(default=0.75)
    ER_REVIEW_THRESHOLD: float = Field(default=0.50)

    # Analytics
    ANALYTICS_COMMUNITY_ALGO: str = Field(default="leiden")   # leiden | louvain
    ANALYTICS_REFRESH_INTERVAL: str = Field(default="weekly")

    # Retrieval
    CONTEXT_BUDGET_TOKENS: int = Field(default=8000)
    CONTEXT_GRAPH_RATIO: float = Field(default=0.4)
    CONTEXT_TEXT_RATIO: float = Field(default=0.4)
    CONTEXT_SUMMARY_RATIO: float = Field(default=0.2)
    RRF_K: int = Field(default=60)

    # Agentic pipeline
    ENABLE_QUERY_ROUTING: bool = Field(default=True)
    ENABLE_PROVENANCE_CHECK: bool = Field(default=True)

    # External enrichment
    SEMANTIC_SCHOLAR_API_KEY: str = Field(default="")

    # Traversal
    MAX_TRAVERSAL_HOPS: int = Field(default=2)  # existing: fixed at 2, now configurable up to 4
```

---

## New Router Entries (`router.py`)

```python
from .modules.analytics.apiv1.handler import router as analytics_router

api_router.include_router(analytics_router, prefix="/v1/analytics", tags=["Analytics"],
                          dependencies=[Depends(get_api_key)])
```

---

## New Endpoints Summary

| Method | Path | Module | Purpose |
|--------|------|--------|---------|
| **Existing** | | | |
| `GET` | `/api/v1/health/ping` | health | Liveness |
| `GET` | `/api/v1/health/status` | health | Readiness + components |
| `GET` | `/api/v1/graph/schema` | graph | Node labels + rel types |
| `GET` | `/api/v1/graph/explore` | graph | Subgraph sample for viz |
| `GET` | `/api/v1/graph/stats` | graph | Node/edge counts |
| `GET` | `/api/v1/graph/nodes/{uid}` | graph | Node detail + rels |
| `GET` | `/api/v1/graph/search` | graph | Full-text node search |
| `POST` | `/api/v1/rag/query` | rag | RAG question answering |
| **New** | | | |
| `GET` | `/api/v1/graph/authors` | graph | List/search authors |
| `GET` | `/api/v1/graph/authors/{id}` | graph | Author detail + papers, co-authors |
| `GET` | `/api/v1/graph/authors/{id}/network` | graph | Co-authorship ego graph |
| `GET` | `/api/v1/graph/orgs` | graph | List/search organizations |
| `GET` | `/api/v1/graph/orgs/{id}` | graph | Org detail + affiliated authors |
| `GET` | `/api/v1/analytics/communities` | analytics | List communities with summaries |
| `GET` | `/api/v1/analytics/communities/{id}` | analytics | Community detail (members, themes) |
| `GET` | `/api/v1/analytics/trends` | analytics | Method/task trend scores |
| `GET` | `/api/v1/analytics/centrality` | analytics | Top authors by PageRank/betweenness |
| `GET` | `/api/v1/analytics/diffusion/{method}` | analytics | Method diffusion timeline |

---

## New CLI Commands

```bash
# Entity Resolution
poetry run cli graph resolve          # Run author/method/org entity resolution
poetry run cli graph resolve --dry    # Preview merges without applying

# Analytics
poetry run cli analytics run          # Run community detection + centrality + trends
poetry run cli analytics status       # Show analytics freshness
poetry run cli analytics summarize    # Generate LLM community summaries

# Evaluation
poetry run cli eval run               # Run all 40 test queries
poetry run cli eval run --category temporal   # Run one category
poetry run cli eval report            # Generate evaluation report
poetry run cli eval compare           # Ablation: plain-RAG vs graph vs hybrid vs LLM-only
```

---

## New neomodel Models (`dbase/neo4j/models/`)

### nodes.py — additions

```python
class Author(BaseNode):
    name = StringProperty(required=True, index=True)
    name_normalized = StringProperty(index=True)
    aliases = ArrayProperty(base_property=StringProperty())
    orcid = StringProperty(unique_index=True)

    papers = RelationshipTo("Paper", "AUTHORED", model=AuthoredRel)
    affiliations = RelationshipTo("Organization", "AFFILIATED_WITH", model=AffiliatedWithRel)
    coauthors = RelationshipTo("Author", "CO_AUTHORED_WITH", model=CoAuthoredWithRel)


class Organization(BaseNode):
    name = StringProperty(required=True, index=True)
    name_normalized = StringProperty(index=True)
    org_type = StringProperty()              # university | company | lab | government
    country = StringProperty()               # ISO 3166-1 alpha-2
    parent_org_uid = StringProperty()         # for hierarchy rollup


class Result(BaseNode):
    metric_name = StringProperty(required=True)
    metric_value = FloatProperty()
    rank = IntegerProperty()
    date = DateProperty()

    paper = RelationshipFrom("Paper", "ACHIEVES_RESULT")
    dataset = RelationshipTo("Dataset", "ON_DATASET")
    task = RelationshipTo("Task", "FOR_TASK")


class Repository(BaseNode):
    url = StringProperty(required=True, unique_index=True)
    framework = StringProperty()             # pytorch | tensorflow | jax | other
    stars = IntegerProperty()
    is_official = BooleanProperty(default=False)

    paper = RelationshipFrom("Paper", "HAS_CODE")
```

### relationships.py — additions

```python
class AuthoredRel(StructuredRel):
    order = IntegerProperty()                # author position (1 = first)
    is_corresponding = BooleanProperty(default=False)

class AffiliatedWithRel(StructuredRel):
    from_date = DateProperty()
    to_date = DateProperty()
    role = StringProperty()

class CoAuthoredWithRel(StructuredRel):
    paper_count = IntegerProperty(default=1)
    first_collab = DateProperty()
    last_collab = DateProperty()

class VariantOfRel(StructuredRel):
    relation_type = StringProperty()         # extension | simplification | combination | alternative
```

### Paper, Method nodes — new relationships

```python
class Paper(BaseNode):
    # ... existing fields ...
    authors = RelationshipFrom("Author", "AUTHORED", model=AuthoredRel)
    methods_used = RelationshipTo("Method", "USES_METHOD")
    methods_introduced = RelationshipTo("Method", "INTRODUCES_METHOD")
    tasks = RelationshipTo("Task", "ADDRESSES_TASK")
    datasets_evaluated = RelationshipTo("Dataset", "EVALUATES_ON")
    results = RelationshipTo("Result", "ACHIEVES_RESULT")
    code = RelationshipTo("Repository", "HAS_CODE")
    cites = RelationshipTo("Paper", "CITES", model=CitesRel)

class Method(BaseNode):
    # ... existing fields ...
    category = StringProperty()
    introduced_date = DateProperty()
    variants = RelationshipTo("Method", "VARIANT_OF", model=VariantOfRel)
```

---

## New LangGraph Pipeline (`library/graph/agentic_pipeline.py`)

```
START
  │
  ▼
analyze_query          ← LLM classifies query type + extracts entities
  │
  ▼
route                  ← conditional edges based on retrieval_strategy
  │
  ├──► graph_retrieve  ← Cypher-based (factual, multi-hop, temporal, network)
  ├──► vector_retrieve ← Neo4j vector search (semantic)
  └──► hybrid_retrieve ← Both in parallel
         │
         ▼
      merge_rerank     ← RRF scoring, dedup, context budget assembly
         │
         ▼
      synthesize       ← LLM generates answer with citations
         │
         ▼
      validate         ← Check provenance: all claims have sources?
         │
         ▼
       END
```

---

## File Count Summary

| Category | Existing | Extend | New | Total |
|----------|----------|--------|-----|-------|
| core/ | 5 | 1 | 0 | 5 |
| dbase/ | 5 | 2 | 0 | 5 |
| shared/ | 4 | 0 | 1 | 5 |
| library/ | 15 | 2 | 13 | 28 |
| modules/health/ | 7 | 0 | 0 | 7 |
| modules/graph/ | 8 | 5 | 0 | 8 |
| modules/rag/ | 7 | 5 | 1 | 8 |
| modules/analytics/ | 0 | 0 | 9 | 9 |
| modules/eval/ | 0 | 0 | 7 | 7 |
| cli/ | 3 | 1 | 0 | 3 |
| root | 2 | 0 | 0 | 2 |
| **Total** | **56** | **16** | **31** | **87** |

**Current**: 56 files → **Full spec**: 87 files (+31 new, 16 extended)
