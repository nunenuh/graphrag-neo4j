# Comparison: Full GraphRAG Spec vs Current Product

**Date**: 2026-03-08
**Reference**: [other-graph-rag-neo4j-specs.md](other-graph-rag-neo4j-specs.md) (the "full spec")
**Our specs**: [specs/](../specs/) (current product implementation)

---

## Executive Summary

Our product implements a solid **Phase 1 foundation** — the core RAG pipeline with a production-quality API. The full spec describes a **6-phase, 6-week system** with entity resolution, temporal reasoning, network analysis, agentic routing, and evaluation harness. Our architecture (LangGraph, neomodel, provider registry) was designed to support these extensions.

| Dimension | Full Spec | Our Product | Coverage |
|-----------|-----------|-------------|----------|
| Core entities (Paper, Method, Task, Dataset) | 4 | 4 | 100% |
| Social entities (Author, Org, Repository) | 3 | 0 | 0% |
| Relationship types | 12 | 2 | 17% |
| Basic RAG pipeline | Yes | Yes | 100% |
| Agentic query routing | 7 strategies | None | 0% |
| Hybrid retrieval (graph+vector+BM25) | Yes | Vector-only seed | ~30% |
| Temporal reasoning | 5 patterns | None | 0% |
| Network analysis | 4 metrics + communities | None | 0% |
| Entity resolution | Full pipeline | None | 0% |
| Evaluation framework | 40 queries, 9 metrics | None | 0% |
| Production API | FastAPI (basic) | FastAPI (full) | Better |
| LLM provider flexibility | 1-2 providers | 4 providers | Better |
| Frontend | Streamlit demo | React + graph viz | Better |

---

## 1. Data Model

### 1.1 Nodes

| Node Type | Full Spec | Our Product | Delta |
|-----------|-----------|-------------|-------|
| `:Paper` | pwc_id, arxiv_id, title, abstract, **date**, url, **url_pdf**, embedding, ingested_at | uid, title, abstract, **year** (string), url, embedding, created_at | Missing: `arxiv_id`, `url_pdf`, `date` as proper date type |
| `:Method` | pwc_id, name, description, **category**, **introduced_date**, embedding | uid, name, full_name, description, embedding | Missing: `category`, `introduced_date` |
| `:Task` | pwc_id, name, area, description | uid, name, area, description | Match |
| `:Dataset` | pwc_id, name, description, **url**, **num_papers**, modalities[] | uid, name, description, modalities, embedding | Missing: `url`, `num_papers`. We added embedding (they didn't) |
| `:Author` | id, name, name_normalized, aliases[], orcid | **Not implemented** | Major gap |
| `:Organization` | id, name, name_normalized, type, country | **Not implemented** | Major gap |
| `:Result` | id, metric_name, metric_value, rank, date | **Not implemented** (flattened into EVALUATED_ON rel props) | Structural gap |
| `:Repository` | id, url, framework, stars, is_official | **Not implemented** | Major gap |

### 1.2 Relationships

| Relationship | Full Spec | Our Product | Status |
|-------------|-----------|-------------|--------|
| `USED_FOR` (Dataset->Task) | Yes | Yes | Match |
| `EVALUATED_ON` (Method->Dataset) | Yes (as Paper->Dataset) | Yes, with metric + score props | Different direction, functional |
| `AUTHORED` (Author->Paper) | Yes, with order + is_corresponding | No Author nodes | Missing |
| `AFFILIATED_WITH` (Author->Org) | Yes, temporal (from_date, to_date) | No Author/Org nodes | Missing |
| `USES_METHOD` (Paper->Method) | Yes | Not implemented | Missing |
| `INTRODUCES_METHOD` (Paper->Method) | Yes | Not implemented | Missing |
| `VARIANT_OF` (Method->Method) | Yes, with relation_type | Not implemented | Missing |
| `ADDRESSES_TASK` (Paper->Task) | Yes | Not implemented | Missing |
| `ACHIEVES_RESULT` / `ON_DATASET` / `FOR_TASK` | Yes, Result node as hub | Flattened into rel props | Missing |
| `HAS_CODE` (Paper->Repository) | Yes | Not implemented | Missing |
| `CITES` (Paper->Paper) | Yes, with citation context | Not implemented | Missing (requires Semantic Scholar) |
| `CO_AUTHORED_WITH` (Author->Author) | Yes, derived with paper_count | Not implemented | Missing |

### 1.3 Derived/Computed Properties

| Property | Full Spec | Our Product | Status |
|----------|-----------|-------------|--------|
| `h_index` on Author | Yes | N/A (no Author) | Missing |
| `pagerank` on Author | Yes (GDS) | N/A | Missing |
| `betweenness` on Author | Yes (GDS) | N/A | Missing |
| `community_id` on Author, Paper | Yes (Leiden) | N/A | Missing |
| `trend_score` on Method, Task | Yes | N/A | Missing |
| `diffusion_path` on Method | Yes | N/A | Missing |

---

## 2. System Architecture

### 2.1 Storage Layer

| Component | Full Spec | Our Product | Notes |
|-----------|-----------|-------------|-------|
| Graph DB | Neo4j Community 5.x + GDS | Neo4j Community (neomodel OGM) | Same DB, no GDS plugin |
| Vector DB | PostgreSQL + pgvector (separate DB) | Neo4j native vector indexes | Simpler: single DB |
| BM25/Lexical search | PostgreSQL tsvector | Not implemented | Gap |

**Trade-off**: The full spec uses two databases (Neo4j + PostgreSQL), giving it BM25 lexical search alongside vector. Our single-DB approach is simpler to deploy and maintain, but lacks lexical search and the pgvector ecosystem.

### 2.2 LLM Integration

| Feature | Full Spec | Our Product | Notes |
|---------|-----------|-------------|-------|
| Provider support | OpenAI + Claude (1-2 providers) | OpenAI, Google, Ollama, Qwen (4 providers) | We're ahead |
| Provider registry | Not specified | Yes, plugin architecture | We're ahead |
| LLM for extraction (ingestion) | Claude/GPT-4 for NER | Not used during ingestion | Gap |
| LLM for synthesis (query) | Claude/GPT-4 | LangChain chat model (any provider) | Match |
| NER tools | spaCy + GLiNER | None | Gap |

### 2.3 Agent Architecture

| Feature | Full Spec | Our Product | Gap Size |
|---------|-----------|-------------|----------|
| Pipeline framework | LangGraph StateGraph | LangGraph StateGraph | Match |
| Pipeline shape | Branching (analyze->route->retrieve->merge->synthesize->validate) | Linear (embed->search->traverse->context->generate) | Major gap |
| Query classification | LLM classifies into 7 types | None — all queries same path | Major gap |
| Retrieval routing | GRAPH_ONLY / VECTOR_ONLY / HYBRID_PARALLEL / HYBRID_SEQUENTIAL | Vector search only | Major gap |
| Merge & reranking | RRF (Reciprocal Rank Fusion) | None | Major gap |
| Provenance validation | Post-synthesis check: all claims cited? | None | Gap |
| Context budget | 8K tokens, 40/40/20 split (graph/text/summary) | Simple concatenation, 30-edge cap | Gap |

**Full spec LangGraph flow:**
```
START -> analyze_query -> route -> [graph_retrieve | vector_retrieve | hybrid_retrieve]
     -> merge_rerank -> synthesize -> validate_provenance -> END
```

**Our LangGraph flow:**
```
START -> embed -> search -> traverse -> context -> generate -> END
```

---

## 3. Pipeline Capabilities

### 3.1 Ingestion

| Capability | Full Spec | Our Product | Status |
|-----------|-----------|-------------|--------|
| Parse PwC JSONs | Yes | Yes | Match |
| Batch embed + upsert | Yes | Yes | Match |
| Relationship MERGE | Yes | Yes | Match |
| Author extraction from paper metadata | Yes, with name normalization | Not implemented | Missing |
| LLM-based entity extraction from abstracts | Yes | Not implemented | Missing |
| Semantic Scholar enrichment (citations, ORCID) | Yes | Not implemented | Missing |
| Delta updates / scheduling | Daily cron, `ingested_at` tracking | Full re-ingest only | Missing |
| Post-load graph analytics (community, centrality) | Yes | Not implemented | Missing |
| Idempotency | MERGE-based | MERGE-based | Match |

### 3.2 Retrieval

| Capability | Full Spec | Our Product | Status |
|-----------|-----------|-------------|--------|
| Vector similarity search | pgvector cosine | Neo4j native vector (neomodel VectorFilter) | Match (different DB) |
| Graph traversal | Cypher, 2-4 hops | Cypher, 2 hops fixed | Partial |
| BM25 lexical search | PostgreSQL tsvector | Not implemented | Missing |
| Hybrid parallel (graph + vector) | Yes, with RRF merge | Not implemented | Missing |
| Hybrid sequential (graph narrows -> vector fills) | Yes | Not implemented | Missing |
| LLM-based reranking | Optional, top-20 | Not implemented | Missing |

### 3.3 Reasoning

| Capability | Full Spec | Our Product | Status |
|-----------|-----------|-------------|--------|
| Single-hop factual | Yes | Yes | Match |
| Multi-hop (2 hops) | Yes | Yes | Match |
| Multi-hop (3-4 hops) | Yes | Not supported (2-hop fixed) | Gap |
| Temporal snapshot ("SOTA in 2022?") | Yes | Not implemented | Missing |
| Temporal trend ("LoRA usage over time") | Yes | Not implemented | Missing |
| Temporal diff ("new methods in 2024 vs 2023") | Yes | Not implemented | Missing |
| Temporal sequence ("before or after joining Org?") | Yes | Not implemented | Missing |
| Method diffusion tracking | Yes | Not implemented | Missing |
| Network analysis (bridge authors) | Yes | Not implemented | Missing |
| Community summaries | Yes, LLM-generated offline | Not implemented | Missing |

---

## 4. Entity Resolution

The full spec has an entire section (Section 4) dedicated to entity resolution. Our product has **none of this**.

| ER Capability | Full Spec | Our Product |
|--------------|-----------|-------------|
| Author name normalization (diacritics, CJK, initials) | Yes | N/A |
| Candidate generation (blocking by last_name + first_initial) | Yes | N/A |
| Similarity scoring (Jaro-Winkler + co-author + topic + affiliation) | Yes | N/A |
| Auto-merge threshold (>= 0.75) | Yes | N/A |
| Human review queue (0.5-0.75) | Yes | N/A |
| ORCID linking override | Yes | N/A |
| Method deduplication (abbreviation expansion + LLM confirmation) | Yes | N/A |
| Organization normalization (hierarchy: "Google Brain" -> "Google") | Yes | N/A |

**Impact**: Without entity resolution, the graph cannot have Author/Organization nodes because raw PwC data has inconsistent author names. This is why our product skips the social graph entirely.

---

## 5. Evaluation Framework

| Capability | Full Spec | Our Product |
|-----------|-----------|-------------|
| Test query set | 40 queries across 7 categories | None |
| Entity Extraction F1 | Target >= 0.85 | N/A |
| Entity Resolution Precision/Recall | Target >= 0.90 / 0.80 | N/A |
| Retrieval Precision@10 / Recall@10 | Target >= 0.70 / 0.60 | N/A |
| Multi-hop Path Accuracy | Target >= 0.75 | N/A |
| Provenance Coverage | Target >= 0.90 | N/A |
| Answer Correctness (LLM judge) | Target >= 0.80 | N/A |
| Latency P95 | <= 5s (1-hop), <= 15s (multi-hop) | N/A |
| Baseline comparisons | 4 systems (plain RAG, graph-only, hybrid, LLM-only) | N/A |

---

## 6. What Our Product Does Better

Despite having less feature coverage, our product excels in several areas:

| Area | Our Advantage | Why It Matters |
|------|---------------|----------------|
| **Provider-agnostic LLM** | 4 providers with plugin registry vs 1-2 hardcoded | Switch providers without code changes; cost optimization |
| **Production API** | Full FastAPI with auth, CORS, health checks, structured errors, OpenAPI docs | Ready for frontend integration, not just a prototype |
| **Clean architecture** | Handler -> UseCase -> Service -> Repository layering | Maintainable, testable, extensible |
| **Single-DB simplicity** | Neo4j for both graph + vector (no PostgreSQL) | Simpler ops, one connection, one backup strategy |
| **Frontend-ready** | React frontend spec with graph visualization, chat panel | Real product UI, not Streamlit demo |
| **Test coverage** | 143 unit tests, 74% coverage, gap analysis documented | Production confidence |
| **neomodel OGM** | Type-safe node models with auto-generated schema | Less raw Cypher, fewer bugs |

---

## 7. Gap Prioritization

If we want to close the gap, here's the recommended priority based on impact and effort:

### Priority 1: High Impact, Moderate Effort

| Feature | Why | Effort | Enables |
|---------|-----|--------|---------|
| **Agentic query routing** | Biggest RAG quality improvement — right strategy per query | 1-2 weeks | All query types |
| **3-4 hop traversal** | Configurable depth, not hardcoded 2 | 2-3 days | Deeper reasoning |
| **Context budget management** | Better LLM answers with structured context allocation | 2-3 days | Answer quality |

### Priority 2: High Impact, High Effort

| Feature | Why | Effort | Enables |
|---------|-----|--------|---------|
| **Author + Organization nodes** | Entire social graph layer — unlocks network analysis | 2-3 weeks | Author queries, network analysis |
| **Entity resolution pipeline** | Required for Author nodes to be useful | 2-3 weeks | Clean social graph |
| **Hybrid retrieval + RRF** | Combines graph structure with semantic similarity | 1-2 weeks | Better retrieval |

### Priority 3: Medium Impact, Moderate Effort

| Feature | Why | Effort | Enables |
|---------|-----|--------|---------|
| **Temporal reasoning** | Time-aware queries (trends, snapshots) | 1 week | Temporal queries |
| **Result node (not rel props)** | Proper benchmark result modeling | 3-5 days | SOTA queries |
| **Paper->Method, Paper->Task edges** | Richer graph structure from existing PwC data | 3-5 days | Factual lookups |
| **Repository nodes + HAS_CODE** | Code availability info | 2-3 days | "Does X have code?" |
| **Provenance validation** | Citation checking in responses | 3-5 days | Trust |

### Priority 4: High Effort, Specialized

| Feature | Why | Effort | Enables |
|---------|-----|--------|---------|
| **Community detection (Leiden)** | Requires Neo4j GDS plugin or networkx fallback | 1-2 weeks | Community summaries |
| **Centrality metrics** | PageRank, betweenness — requires GDS or networkx | 1 week | Influence queries |
| **Evaluation harness** | 40 test queries + automated scoring | 2-3 weeks | Quality measurement |
| **BM25 lexical search** | Requires adding PostgreSQL or alternative | 1-2 weeks | Keyword search |
| **Semantic Scholar enrichment** | External API integration for citations | 1 week | Citation graph |
| **LLM-based NER** | Extract entities from abstracts | 1-2 weeks | Richer graph |

---

## 8. Mapping to Full Spec Phases

| Full Spec Phase | Timeline | Our Status |
|----------------|----------|------------|
| **Phase 1**: Foundation (parse, schema, ingest, embed) | Week 1-2 | **Done** |
| **Phase 2**: Entity Resolution (author dedup, org normalization) | Week 3 | Not started |
| **Phase 3**: Graph Analytics (Leiden, PageRank, trends) | Week 3-4 | Not started |
| **Phase 4**: LangGraph Agent (router, hybrid retrieval, synthesizer) | Week 4-5 | Partially done (linear pipeline only) |
| **Phase 5**: Evaluation (40 queries, metrics, ablation) | Week 5-6 | Not started |
| **Phase 6**: Polish & Document (API, UI, docs) | Week 6 | **Done** (ahead of spec — we have production API + React spec) |

**Our position**: Phase 1 complete + Phase 6 done early. Phases 2-5 are the gap.
