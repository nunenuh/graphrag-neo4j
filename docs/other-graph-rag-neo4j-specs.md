# GraphRAG System Specification: Papers with Code Domain

**Version**: 0.1.0-draft
**Author**: Fandi (Lalu Erfandi Maula Yusnu)
**Date**: 2026-03-08
**Status**: Draft — Iteration 1 of ~3

---

## 0. Document Purpose

Technical specification for building a **Graph-based Retrieval-Augmented Generation (GraphRAG)** system using the **Papers with Code (PwC)** dataset as the knowledge domain. This covers the ~70% of graph-based retrieval, reasoning, and generation that the PwC dataset can effectively test.

**This is NOT an intelligence reporting system.** It is a research knowledge graph + RAG system optimized for multi-hop reasoning over academic ML/AI research entities.

---

## 1. Scope & Boundaries

### 1.1 In Scope

- Knowledge graph construction from PwC structured data
- Entity extraction, resolution, and linking pipeline
- Multi-hop graph retrieval (2-4 hops)
- Temporal reasoning over publication timelines
- Community/cluster detection and summarization
- Network analysis (collaboration, influence, method diffusion)
- Hybrid retrieval (graph traversal + vector similarity)
- Agentic query decomposition via LangGraph
- Evaluation harness (precision, recall, path accuracy, provenance)

### 1.2 Out of Scope (the remaining ~30%)

- Source reliability scoring (Admiralty system) — PwC sources are uniformly reliable
- Competing hypothesis generation (ACH) — insufficient contradictory data in PwC
- Access control / compartmentation — all PwC data is public
- Real-time streaming ingestion — PwC updates daily (batch)
- Multimodal fusion (imagery, audio, signals) — PwC is text-structured data
- Report generation with classification markings

### 1.3 Constraints

| Constraint | Value |
|---|---|
| Target team size | 1-2 engineers (Fandi + optional ML engineer) |
| Infra budget | Low — self-hosted or free-tier services |
| Primary stack | Python, LangGraph, PostgreSQL (pgvector), Neo4j Community |
| LLM dependency | Claude / GPT-4 for extraction; local model fallback for cost control |
| Data license | PwC data is CC-BY-SA |

### 1.4 Assumptions

- PwC dataset is available via GitHub (`paperswithcode/paperswithcode-data`) or API client (`paperswithcode-client`)
- Neo4j Community Edition is sufficient (no enterprise RBAC needed)
- LLM-based entity extraction is acceptable for initial graph construction (with human spot-check)
- pgvector is already available in existing PostgreSQL setup

---

## 2. Data Model

### 2.1 Source Data (PwC JSON Files)

PwC provides the following core JSON dumps (regenerated daily):

| File | Contents | Key Fields |
|---|---|---|
| `papers-with-abstracts.json` | Papers + abstracts | id, arxiv_id, title, abstract, date, authors, url_pdf |
| `datasets.json` | Benchmark datasets | id, name, description, url, tasks |
| `methods.json` | ML methods/techniques | id, name, description, paper, category |
| `evaluation-tables.json` | SOTA benchmark results | task, dataset, metrics, rows (model, paper, scores) |
| `links-between-papers-and-code.json` | Paper ↔ code repos | paper_id, repo_url, framework |

### 2.2 Graph Schema (Neo4j)

#### Nodes

```
(:Paper {
  pwc_id: string,          // PwC internal ID
  arxiv_id: string,        // arXiv identifier (nullable)
  title: string,
  abstract: string,        // full abstract text
  date: date,              // publication date
  url: string,             // link to paper
  url_pdf: string,         // direct PDF link
  embedding: float[],      // abstract embedding vector (populated in Phase 2)
  ingested_at: datetime    // when this node was created
})

(:Author {
  id: string,              // generated UUID or PwC-derived
  name: string,            // display name
  name_normalized: string, // lowercase, stripped diacritics for matching
  aliases: string[],       // known alternate names
  orcid: string            // nullable, if resolvable
})

(:Organization {
  id: string,
  name: string,
  name_normalized: string,
  type: string,            // "university" | "company" | "lab" | "government"
  country: string          // ISO 3166-1 alpha-2
})

(:Method {
  pwc_id: string,
  name: string,
  description: string,
  category: string,        // e.g., "Attention", "Normalization", "Loss Function"
  introduced_date: date,   // date of the paper that introduced it
  embedding: float[]       // description embedding
})

(:Task {
  pwc_id: string,
  name: string,
  area: string,            // e.g., "Computer Vision", "NLP", "RL"
  description: string
})

(:Dataset {
  pwc_id: string,
  name: string,
  description: string,
  url: string,
  num_papers: int,         // count of papers using this dataset
  modalities: string[]     // ["image", "text", "audio", etc.]
})

(:Result {
  id: string,              // generated
  metric_name: string,     // e.g., "Top-1 Accuracy", "F1", "BLEU"
  metric_value: float,
  rank: int,               // SOTA rank at time of publication (nullable)
  date: date               // inherited from paper date
})

(:Repository {
  id: string,
  url: string,             // GitHub/GitLab URL
  framework: string,       // "pytorch" | "tensorflow" | "jax" | "other"
  stars: int,              // GitHub stars (nullable, snapshot)
  is_official: boolean     // official author implementation vs community
})
```

#### Edges

```
// Authorship
(:Author)-[:AUTHORED {
  order: int,              // author position (1 = first author)
  is_corresponding: boolean
}]->(:Paper)

// Affiliation (temporal)
(:Author)-[:AFFILIATED_WITH {
  from_date: date,         // nullable — inferred from paper dates
  to_date: date,           // nullable — null means "current"
  role: string             // nullable — "PhD Student", "Professor", "Researcher"
}]->(:Organization)

// Method usage
(:Paper)-[:USES_METHOD]->(:Method)

// Method introduced
(:Paper)-[:INTRODUCES_METHOD]->(:Method)

// Method lineage
(:Method)-[:VARIANT_OF {
  relation_type: string    // "extension" | "simplification" | "combination" | "alternative"
}]->(:Method)

// Task addressed
(:Paper)-[:ADDRESSES_TASK]->(:Task)

// Dataset evaluation
(:Paper)-[:EVALUATES_ON {
  split: string            // "test" | "val" | "dev" (nullable)
}]->(:Dataset)

// Benchmark result
(:Paper)-[:ACHIEVES_RESULT]->(:Result)
(:Result)-[:ON_DATASET]->(:Dataset)
(:Result)-[:FOR_TASK]->(:Task)

// Code link
(:Paper)-[:HAS_CODE]->(:Repository)

// Citation (if enriched from Semantic Scholar)
(:Paper)-[:CITES {
  context: string          // nullable — citation context sentence
}]->(:Paper)

// Co-authorship (derived, for network analysis)
(:Author)-[:CO_AUTHORED_WITH {
  paper_count: int,        // number of shared papers
  first_collab: date,
  last_collab: date
}]->(:Author)
```

### 2.3 Derived/Computed Properties

These are not in source data but computed during ingestion or as background jobs:

| Property | On | Computation |
|---|---|---|
| `h_index` | Author | Count papers with >= h citations |
| `pagerank` | Author | PageRank on co-authorship graph |
| `betweenness` | Author | Betweenness centrality (bridge authors) |
| `community_id` | Author, Paper | Leiden/Louvain community detection |
| `trend_score` | Method, Task | Growth rate of usage over time windows |
| `diffusion_path` | Method | Ordered list of orgs that adopted the method |

---

## 3. System Architecture

### 3.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Orchestrator                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Query    │  │  Router  │  │  Multi-  │  │  Response   │  │
│  │  Analyzer │→ │  (graph/ │→ │  Step    │→ │  Synthesizer│  │
│  │          │  │  vector/ │  │  Executor│  │  + Citation │  │
│  │          │  │  hybrid) │  │          │  │            │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└────────┬────────────┬─────────────┬──────────────────────────┘
         │            │             │
         ▼            ▼             ▼
┌────────────┐ ┌─────────────┐ ┌──────────────┐
│   Neo4j    │ │  PostgreSQL │ │   LLM API    │
│   (Graph)  │ │  (pgvector) │ │  (Claude /   │
│            │ │             │ │   GPT-4)     │
│ - Cypher   │ │ - Semantic  │ │              │
│ - Traverse │ │   search    │ │ - Extraction │
│ - Community│ │ - BM25 via  │ │ - Synthesis  │
│ - Network  │ │   tsvector  │ │ - Reasoning  │
│   analysis │ │             │ │              │
└────────────┘ └─────────────┘ └──────────────┘
```

### 3.2 Component Breakdown

#### 3.2.1 Data Ingestion Pipeline

**Input**: PwC JSON dumps + optional enrichment (Semantic Scholar citations, ORCID)

**Pipeline steps**:

1. **Parse**: Load PwC JSONs → normalize into intermediate dataclasses
2. **Entity Extraction (Authors)**:
   - Parse author names from PwC paper records
   - Normalize: lowercase, strip diacritics, handle CJK names
   - Fuzzy dedup: Levenshtein distance < 2 on normalized names within same paper topic cluster → candidate merge
   - Affiliation extraction: LLM-based extraction from abstracts/paper metadata (fallback: Semantic Scholar API)
3. **Entity Extraction (Methods)**:
   - Primary: Use PwC `methods.json` (structured, high quality)
   - Secondary: LLM extraction from abstracts for methods not in PwC's catalog
   - Link: `VARIANT_OF` edges via LLM classification ("Is Method B a variant of Method A?")
4. **Relationship Construction**:
   - `AUTHORED`: Direct from PwC data (author order preserved)
   - `USES_METHOD`, `ADDRESSES_TASK`, `EVALUATES_ON`: Direct from PwC data
   - `CITES`: Requires Semantic Scholar enrichment (PwC doesn't include citations)
   - `CO_AUTHORED_WITH`: Derived — for each paper, create edges between all author pairs
   - `AFFILIATED_WITH`: Inferred from author metadata or LLM extraction
5. **Embedding Generation**:
   - Embed: Paper abstracts, Method descriptions, Dataset descriptions
   - Model: `text-embedding-3-small` (OpenAI) or `all-MiniLM-L6-v2` (local)
   - Store: pgvector column on corresponding PostgreSQL mirror table
6. **Graph Analytics (post-load)**:
   - Run Leiden community detection → assign `community_id` to Author and Paper nodes
   - Compute PageRank, betweenness centrality on co-authorship graph
   - Compute method trend scores (papers/month using method, rolling 6-month window)

**Idempotency**: Each run should be idempotent. Use `pwc_id` as merge key. `MERGE` in Cypher, `ON CONFLICT DO UPDATE` in PostgreSQL.

**Scheduling**: Daily cron (aligned with PwC data refresh). Delta updates only — track `ingested_at` timestamps.

#### 3.2.2 Query Router (LangGraph Node)

Classifies incoming queries into retrieval strategy:

| Query Type | Detection Signal | Retrieval Strategy |
|---|---|---|
| **Factual lookup** | "What methods does Paper X use?" | Direct Cypher query |
| **Semantic search** | "Papers about few-shot learning for medical images" | pgvector similarity search |
| **Multi-hop traversal** | "Which authors who worked on X later moved to Org Y?" | Graph traversal (2+ hops) |
| **Temporal trend** | "How has attention mechanism usage evolved since 2020?" | Time-windowed aggregation |
| **Network analysis** | "Who are the bridge authors between CV and NLP?" | Centrality / community queries |
| **Comparison** | "Compare Transformer vs Mamba architectures across benchmarks" | Hybrid (graph + vector) |
| **Global summary** | "What are the main research themes in 2025?" | Community summaries |

**Implementation**: LLM-based classifier with structured output. Input = user query. Output = `{query_type, entities_mentioned, time_range, hops_needed}`.

#### 3.2.3 Retrieval Executors

**A. Graph Retriever (Neo4j)**

Translates query plan into Cypher. Examples:

```cypher
// Multi-hop: Authors who used Method A and also collaborated with Org B members
MATCH (a:Author)-[:AUTHORED]->(p:Paper)-[:USES_METHOD]->(m:Method {name: $method})
MATCH (a)-[:CO_AUTHORED_WITH]->(b:Author)-[:AFFILIATED_WITH]->(o:Organization {name: $org})
WHERE p.date >= date($start_date)
RETURN a.name, b.name, p.title, p.date
ORDER BY p.date DESC
LIMIT 20

// Temporal: Method adoption over time
MATCH (p:Paper)-[:USES_METHOD]->(m:Method {name: $method})
WITH m, p.date.year AS year, p.date.month AS month, count(p) AS paper_count
RETURN year, month, paper_count
ORDER BY year, month

// Network: Bridge authors between two communities
MATCH (a:Author)
WHERE a.community_id = $community_1
WITH collect(a) AS comm1
MATCH (b:Author)
WHERE b.community_id = $community_2
WITH comm1, collect(b) AS comm2
UNWIND comm1 AS a
MATCH (a)-[:CO_AUTHORED_WITH]-(bridge)-[:CO_AUTHORED_WITH]-(b)
WHERE b IN comm2 AND NOT bridge IN comm1 AND NOT bridge IN comm2
RETURN bridge.name, count(DISTINCT a) AS conn_to_comm1, count(DISTINCT b) AS conn_to_comm2
ORDER BY conn_to_comm1 + conn_to_comm2 DESC
LIMIT 10
```

**B. Vector Retriever (pgvector)**

For semantic similarity when graph structure alone is insufficient:

```sql
-- Semantic search on paper abstracts
SELECT id, title, abstract, date,
       1 - (embedding <=> $query_embedding) AS similarity
FROM papers
WHERE date >= $start_date
ORDER BY embedding <=> $query_embedding
LIMIT $k;

-- Hybrid: BM25 + vector
SELECT id, title,
       ts_rank(tsv, plainto_tsquery($query)) AS bm25_score,
       1 - (embedding <=> $query_embedding) AS semantic_score,
       (0.4 * ts_rank(tsv, plainto_tsquery($query)) +
        0.6 * (1 - (embedding <=> $query_embedding))) AS hybrid_score
FROM papers
WHERE tsv @@ plainto_tsquery($query)
ORDER BY hybrid_score DESC
LIMIT $k;
```

**C. Hybrid Retriever**

Combines graph and vector results:

1. Graph retriever returns structured entity/relationship data
2. Vector retriever returns semantically similar text chunks
3. Merge: Graph results provide structure; vector results fill semantic gaps
4. Rerank: Cross-encoder or LLM-based reranker scores combined results

#### 3.2.4 Response Synthesizer (LangGraph Node)

Takes retrieved context (graph paths + text chunks) and generates the final response.

**Requirements**:
- Every factual claim must include a `source` reference (paper ID, author name, etc.)
- Provenance chain: `claim → retrieved_path → source_paper(s)`
- If graph traversal was used, include the path in metadata (for debugging/audit)

**Prompt template structure**:

```
You are a research analysis assistant. Answer the user's question using ONLY
the provided context. For every claim, cite the source paper(s) by title and date.

## Retrieved Graph Context
{graph_results}

## Retrieved Semantic Context
{vector_results}

## Graph Paths Used
{traversal_paths}

## User Question
{query}

## Instructions
- Cite every factual claim with [Paper Title, Year]
- If evidence is insufficient, say so explicitly
- If results conflict, present both sides with citations
- Structure your answer with clear sections if the question is complex
```

#### 3.2.5 Community Summary Generator (Offline)

Pre-computed summaries for each detected community (Leiden clusters):

1. For each community, collect all papers, authors, methods, tasks
2. Generate a 200-word summary via LLM:
   - Key research themes
   - Central authors (by PageRank within community)
   - Dominant methods and datasets
   - Temporal arc (when did this community emerge, peak, decline?)
3. Store summaries as `(:CommunitySummary)` nodes linked to community members
4. Refresh: Weekly or on significant graph changes

---

## 4. Entity Resolution Specification

Entity resolution is **the single most critical pipeline** for graph quality. Bad ER = phantom connections or missed links.

### 4.1 Author Disambiguation

**Problem**: Same author appears with different name formats across papers.

| Variation Type | Example |
|---|---|
| First name vs initial | "Yoshua Bengio" vs "Y. Bengio" |
| Diacritics | "François" vs "Francois" |
| Name order | "Ming-Wei Chang" vs "Chang, Ming-Wei" |
| CJK romanization | "Yann LeCun" vs "Yan LeCun" |
| Hyphenation | "Jean-Pierre" vs "Jean Pierre" |
| Middle name | "Geoffrey E. Hinton" vs "Geoffrey Hinton" |

**Resolution pipeline**:

```
Step 1: Normalize
  - Lowercase all names
  - Strip diacritics (NFD decomposition → remove combining chars)
  - Standardize to "firstname lastname" order
  - Remove middle initials for matching (keep in display name)

Step 2: Candidate generation
  - Blocking: Group by (last_name, first_initial)
  - Within each block: compute pairwise similarity

Step 3: Similarity scoring
  - Name similarity: Jaro-Winkler on normalized full name (weight: 0.3)
  - Co-author overlap: Jaccard on co-author sets (weight: 0.3)
  - Topic similarity: cosine on aggregated paper embeddings (weight: 0.2)
  - Affiliation overlap: exact match on organization (weight: 0.2)
  - Threshold: combined score >= 0.75 → auto-merge
  - Score 0.5-0.75 → flag for human review

Step 4: Merge
  - Keep all aliases in `aliases[]` field
  - Primary name = most frequent variant
  - ORCID linking (if available) overrides all heuristics
```

**Enrichment source**: Semantic Scholar API provides author IDs and ORCID links. Use as ground truth where available.

### 4.2 Method Deduplication

**Problem**: Same method referenced with different names.

| Canonical | Variants |
|---|---|
| "Multi-Head Attention" | "MHA", "multi-head self-attention", "Multi-Head Attn" |
| "Batch Normalization" | "BatchNorm", "BN", "batch norm" |
| "Residual Connection" | "skip connection", "shortcut connection", "ResConnect" |

**Resolution**:
- Primary: Use PwC's method catalog as canonical source
- Abbreviation expansion: maintain lookup table (community-contributed or LLM-generated)
- Embedding similarity: cosine on method descriptions > 0.9 → candidate merge
- LLM confirmation: "Are 'skip connection' and 'residual connection' the same method?" → structured yes/no

### 4.3 Organization Normalization

**Problem**: "Google" vs "Google Research" vs "Google Brain" vs "Google DeepMind"

**Approach**:
- Maintain a curated org hierarchy (org → parent_org)
- e.g., "Google Brain" → parent: "Google", "Google DeepMind" → parent: "Google"
- For queries: option to resolve at entity level or roll up to parent
- Initial seed: manually curate top ~200 organizations in ML/AI (covers ~80% of papers)
- Long tail: LLM classification for new orgs

---

## 5. Temporal Reasoning Specification

### 5.1 Temporal Data Model

Every temporal entity carries:

```
{
  date: date,              // primary timestamp (paper publication date)
  date_granularity: string // "day" | "month" | "year"
}
```

Edges with temporal dimension:

```
(:Author)-[:AFFILIATED_WITH {from_date, to_date}]->(:Organization)
(:Author)-[:CO_AUTHORED_WITH {first_collab, last_collab, paper_count}]->(:Author)
```

### 5.2 Temporal Query Patterns

| Pattern | Cypher Template |
|---|---|
| **Snapshot** — "Who was SOTA on ImageNet in 2022?" | `WHERE r.date <= date('2022-12-31') ORDER BY r.metric_value DESC LIMIT 1` |
| **Trend** — "How has usage of LoRA changed over time?" | Aggregate `count(p)` grouped by `p.date.year, p.date.quarter` |
| **Diff** — "What methods emerged in 2024 that didn't exist in 2023?" | Set difference: methods with `introduced_date` in 2024 minus those in 2023 |
| **Sequence** — "Did Author X use Method A before or after joining Org Y?" | Compare `p.date` (paper using method) with `aff.from_date` (affiliation) |
| **Diffusion** — "Track how Transformer attention spread from NLP to CV" | Time-ordered list of `(paper.date, paper.task.area)` for papers using the method |

### 5.3 Time Window Functions

For trend analysis, define standard windows:

```python
WINDOWS = {
    "monthly": {"unit": "month", "count": 1},
    "quarterly": {"unit": "month", "count": 3},
    "yearly": {"unit": "year", "count": 1},
    "rolling_6m": {"unit": "month", "count": 6, "rolling": True},
}
```

Trend score for a method:

```
trend_score(method, window) =
    (papers_in_current_window - papers_in_previous_window) / papers_in_previous_window
```

Positive = growing adoption. Negative = declining. Used for "what's trending" queries.

---

## 6. Network Analysis Specification

### 6.1 Community Detection

**Algorithm**: Leiden (preferred over Louvain — better quality, guaranteed connected communities)

**Execution**: Run on co-authorship graph using Neo4j GDS (Graph Data Science) library

```cypher
// Project graph
CALL gds.graph.project('coauthor', 'Author', 'CO_AUTHORED_WITH',
  {relationshipProperties: 'paper_count'})

// Run Leiden
CALL gds.leiden.write('coauthor', {
  writeProperty: 'community_id',
  relationshipWeightProperty: 'paper_count',
  maxLevels: 10,
  gamma: 1.0
})
```

**Output**: Each Author node gets `community_id`. Papers inherit community from majority-author community.

**Refresh cadence**: Weekly (communities are relatively stable).

### 6.2 Centrality Metrics

| Metric | What It Reveals | Computation |
|---|---|---|
| **PageRank** | Overall influence | GDS `gds.pageRank.write` on co-authorship |
| **Betweenness** | Bridge/broker role | GDS `gds.betweenness.write` — high = connects communities |
| **Degree** | Collaboration breadth | Count of distinct co-authors |
| **Closeness** | Access to information | GDS `gds.closeness.write` — low distance to all others |

Store all centrality scores as node properties. Update weekly.

### 6.3 Diffusion Tracking

For method diffusion analysis ("How did Attention spread from NLP to CV?"):

```cypher
// Get time-ordered adoption path across research areas
MATCH (p:Paper)-[:USES_METHOD]->(m:Method {name: $method})
MATCH (p)-[:ADDRESSES_TASK]->(t:Task)
WITH t.area AS area, p.date AS date, p.title AS paper
ORDER BY date ASC
WITH area, collect({date: date, paper: paper})[0] AS first_paper
RETURN area, first_paper.date AS first_adopted, first_paper.paper AS introducing_paper
ORDER BY first_adopted ASC
```

This produces the diffusion timeline: which research area adopted the method first, second, etc.

---

## 7. Hybrid Retrieval Pipeline

### 7.1 Retrieval Strategy Selection

The query analyzer classifies into one of:

| Strategy | When | Components |
|---|---|---|
| `GRAPH_ONLY` | Explicit entity/relationship queries | Neo4j Cypher |
| `VECTOR_ONLY` | Broad semantic/topical queries | pgvector similarity |
| `HYBRID_PARALLEL` | Complex queries needing both structure + semantics | Both in parallel → merge |
| `HYBRID_SEQUENTIAL` | Graph narrows scope → vector fills detail | Graph first → vector on subgraph |

### 7.2 Merge & Reranking

When both retrievers return results:

1. **Normalize scores**: Graph results get relevance score from path length + node centrality. Vector results have cosine similarity.
2. **Reciprocal Rank Fusion (RRF)**:
   ```
   RRF_score(doc) = Σ 1 / (k + rank_i(doc))  for each retriever i
   ```
   where `k = 60` (standard constant).
3. **Optional LLM reranker**: For top-20 merged results, ask LLM to rerank by relevance to query. Expensive but highest quality.
4. **Dedup**: Same paper from both retrievers → keep highest score, merge metadata.

### 7.3 Context Assembly

Final context window for the LLM synthesizer:

```
Context budget: ~8,000 tokens (configurable)

Allocation:
  - Graph paths / structured results:  40% (~3,200 tokens)
  - Text chunks (abstracts):           40% (~3,200 tokens)
  - Community summaries (if global):   20% (~1,600 tokens)
```

Prioritize:
- Most recent results (temporal recency bias for trend queries)
- Highest centrality sources (PageRank-weighted)
- Direct evidence over inferred connections

---

## 8. LangGraph Agent Architecture

### 8.1 Graph Definition

```
                    ┌─────────────┐
                    │  START       │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  analyze_   │
                    │  query      │  → classify query type, extract entities,
                    └──────┬──────┘    determine time range, estimate hops
                           │
                    ┌──────┴──────┐
                    │  route      │  → select retrieval strategy
                    └──┬───┬───┬──┘
                       │   │   │
            ┌──────────┘   │   └──────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ graph_     │ │ vector_    │ │ hybrid_    │
     │ retrieve   │ │ retrieve   │ │ retrieve   │
     └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
           │              │              │
           └──────────┬───┘──────────────┘
                      │
                      ▼
               ┌─────────────┐
               │  merge_     │  → RRF, dedup, context assembly
               │  rerank     │
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │  synthesize  │  → LLM generates answer with citations
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │  validate    │  → check: all claims cited?
               │  provenance  │     any hallucinated entities?
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │  END         │
               └─────────────┘
```

### 8.2 State Schema

```python
from typing import TypedDict, Literal

class QueryAnalysis(TypedDict):
    query_type: Literal[
        "factual_lookup",
        "semantic_search",
        "multi_hop",
        "temporal_trend",
        "network_analysis",
        "comparison",
        "global_summary"
    ]
    entities: list[dict]           # [{type: "author", value: "Yann LeCun"}, ...]
    time_range: dict | None        # {start: "2020-01-01", end: "2024-12-31"}
    hops_needed: int               # estimated traversal depth
    retrieval_strategy: Literal[
        "GRAPH_ONLY", "VECTOR_ONLY", "HYBRID_PARALLEL", "HYBRID_SEQUENTIAL"
    ]

class RetrievalResult(TypedDict):
    source: Literal["graph", "vector"]
    items: list[dict]              # retrieved items with metadata
    cypher_query: str | None       # for graph results — audit trail
    sql_query: str | None          # for vector results — audit trail

class GraphRAGState(TypedDict):
    query: str                     # original user query
    analysis: QueryAnalysis
    graph_results: list[RetrievalResult]
    vector_results: list[RetrievalResult]
    merged_context: str            # assembled context for LLM
    response: str                  # final generated answer
    citations: list[dict]          # [{claim: "...", sources: ["paper_id_1", ...]}]
    provenance_valid: bool         # all claims have sources?
```

### 8.3 Conditional Edges

```python
def route_query(state: GraphRAGState) -> str:
    strategy = state["analysis"]["retrieval_strategy"]
    if strategy == "GRAPH_ONLY":
        return "graph_retrieve"
    elif strategy == "VECTOR_ONLY":
        return "vector_retrieve"
    else:
        return "hybrid_retrieve"  # runs both in parallel
```

---

## 9. Evaluation Framework

### 9.1 Test Query Categories

Design **minimum 40 test queries** across categories:

| Category | Count | Example |
|---|---|---|
| **Single-hop factual** | 8 | "What methods does ResNet use?" |
| **Multi-hop (2 hops)** | 8 | "Which datasets were used by papers that cite Attention Is All You Need?" |
| **Multi-hop (3+ hops)** | 6 | "Authors who co-authored with someone at Google and later published on RL at a university" |
| **Temporal trend** | 6 | "How has the usage of Diffusion Models changed from 2020 to 2025?" |
| **Network/community** | 4 | "Who are the most influential bridge authors between NLP and CV?" |
| **Comparison** | 4 | "Compare ViT vs CNN architectures on ImageNet benchmarks over time" |
| **Global summary** | 4 | "What are the dominant research themes in 2024?" |

### 9.2 Metrics

| Metric | What It Measures | Target |
|---|---|---|
| **Entity Extraction F1** | NER quality on author/method/dataset extraction | ≥ 0.85 |
| **Entity Resolution Precision** | Correct merges / total merges | ≥ 0.90 |
| **Entity Resolution Recall** | Correct merges / total true matches | ≥ 0.80 |
| **Retrieval Precision@10** | Relevant items in top-10 results | ≥ 0.70 |
| **Retrieval Recall@10** | Found relevant items / total relevant | ≥ 0.60 |
| **Multi-hop Path Accuracy** | Correct traversal paths / total multi-hop queries | ≥ 0.75 |
| **Provenance Coverage** | Claims with valid source citations / total claims | ≥ 0.90 |
| **Answer Correctness (LLM judge)** | LLM-as-judge on generated vs gold answer | ≥ 0.80 |
| **Latency P95** | 95th percentile response time | ≤ 5s (single-hop), ≤ 15s (multi-hop) |

### 9.3 Evaluation Pipeline

```
For each test query:
  1. Run full pipeline → get response + citations
  2. Compare retrieved entities against gold set → Precision/Recall
  3. Verify each citation traces to real paper → Provenance Coverage
  4. LLM judge scores response vs gold answer → Correctness
  5. Measure wall-clock time → Latency

Aggregate:
  - Per-category scores (which query types are weakest?)
  - Graph-only vs vector-only vs hybrid comparison
  - Error analysis: categorize failures (wrong entity, missed hop, hallucination, etc.)
```

### 9.4 Baseline Comparisons

Run the same 40 queries against:

| System | Purpose |
|---|---|
| **Plain RAG** (pgvector only, chunked abstracts) | Baseline — what does graph add? |
| **GraphRAG** (Neo4j + LangGraph, no vector) | Graph-only value |
| **Hybrid** (Neo4j + pgvector + LangGraph) | Full system |
| **LLM-only** (no retrieval, just Claude/GPT-4) | How much does the LLM already know? |

This gives you a clean ablation study showing the marginal value of each component.

---

## 10. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Graph DB** | Neo4j Community 5.x | Free, mature, Cypher, GDS library for analytics |
| **Vector DB** | PostgreSQL + pgvector | Already in stack, avoid new infra |
| **Search** | PostgreSQL tsvector (BM25) | Lexical search alongside vector, same DB |
| **Agent framework** | LangGraph | Already in stack, state machine for multi-step |
| **Embeddings** | `all-MiniLM-L6-v2` (local) or `text-embedding-3-small` (API) | Cost vs quality tradeoff |
| **LLM (extraction)** | Claude Sonnet 4 (API) | Entity/relationship extraction during ingestion |
| **LLM (synthesis)** | Claude Sonnet 4 or Opus 4 | Response generation |
| **NER** | spaCy + GLiNER | Author/org extraction from unstructured text |
| **Entity resolution** | Custom (Jaro-Winkler + co-author overlap) | Lightweight, no Senzing needed for PwC scale |
| **Eval** | RAGAS + custom metrics | Standard RAG eval + graph-specific metrics |
| **Orchestration** | Python 3.11+ | Consistency with existing stack |
| **Data pipeline** | Prefect or simple cron + Python scripts | Lightweight scheduling |

---

## 11. Implementation Phases

### Phase 1: Foundation (Week 1-2)

- [ ] Download PwC dataset, write JSON parsers
- [ ] Define Neo4j schema, write Cypher `CREATE CONSTRAINT` / `CREATE INDEX`
- [ ] Build ingestion pipeline: JSON → Neo4j (Papers, Authors, Methods, Tasks, Datasets, Results)
- [ ] Build pgvector mirror: papers table with embeddings
- [ ] Basic Cypher query interface (manual testing)
- [ ] **Deliverable**: Populated graph + vector DB, basic query capability

### Phase 2: Entity Resolution (Week 3)

- [ ] Author name normalization pipeline
- [ ] Fuzzy matching + co-author overlap scoring
- [ ] Human review interface for ambiguous merges (simple CLI or Streamlit)
- [ ] Organization normalization (top 200 manual, rest LLM-assisted)
- [ ] Method deduplication
- [ ] **Deliverable**: Clean, deduplicated graph with ER metrics

### Phase 3: Graph Analytics (Week 3-4)

- [ ] Install Neo4j GDS plugin
- [ ] Run Leiden community detection
- [ ] Compute centrality metrics (PageRank, betweenness)
- [ ] Generate community summaries (LLM-based, offline batch)
- [ ] Compute method trend scores
- [ ] **Deliverable**: Analytics-enriched graph, community summaries

### Phase 4: LangGraph Agent (Week 4-5)

- [ ] Query analyzer node (classify + extract entities)
- [ ] Query router (graph/vector/hybrid selection)
- [ ] Graph retriever (Cypher generation from query plan)
- [ ] Vector retriever (pgvector similarity + BM25)
- [ ] Hybrid merger + RRF reranking
- [ ] Response synthesizer with citation injection
- [ ] Provenance validator
- [ ] **Deliverable**: Working end-to-end query pipeline

### Phase 5: Evaluation (Week 5-6)

- [ ] Design 40 test queries with gold answers
- [ ] Build eval harness (automated scoring)
- [ ] Run baseline comparison (plain RAG vs graph-only vs hybrid vs LLM-only)
- [ ] Error analysis and iteration
- [ ] **Deliverable**: Evaluation report with ablation results

### Phase 6: Polish & Document (Week 6)

- [ ] API interface (FastAPI wrapper)
- [ ] Streamlit demo UI
- [ ] Documentation (this spec + API docs + runbook)
- [ ] **Deliverable**: Demo-ready system with documentation

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Author disambiguation errors cascade through graph | High — wrong co-authorship links | Conservative merge threshold (0.75), human review for borderline |
| Neo4j GDS not available on Community Edition | Medium — can't run Leiden/PageRank | Use `networkx` in Python as fallback (slower but functional) |
| LLM extraction hallucinations during ingestion | High — phantom entities in graph | Validate extracted entities against PwC structured data; discard unmatched |
| PwC data schema changes | Low — breaks parser | Pin to specific data snapshot for testing; version parsers |
| Citation data missing (PwC doesn't include citations) | Medium — limits multi-hop | Enrich from Semantic Scholar API (free tier: 100 req/sec) |
| Cost overrun on LLM API calls during ingestion | Medium | Batch extraction, cache results, use local models for high-volume NER |
| Query latency on large graph (>100K papers) | Medium | Neo4j indexing on pwc_id, date; limit traversal depth to 4 hops |

---

## 13. Success Criteria

The system is considered **successful** if:

1. **Multi-hop queries outperform plain RAG by ≥ 30%** on path accuracy metric
2. **Provenance coverage ≥ 90%** — virtually every claim traces to a source paper
3. **Entity resolution precision ≥ 90%** — minimal phantom connections
4. **End-to-end latency ≤ 15s** for the hardest multi-hop queries
5. **The system can answer questions that plain RAG fundamentally cannot** — e.g., "trace the diffusion of Attention mechanism from NLP to CV through specific authors and papers"

---

## 14. Future Extensions (Post-MVP)

If the PwC system validates the architecture, these extensions map to the remaining ~30% for intel-grade systems:

| Extension | What It Adds | Complexity |
|---|---|---|
| Source reliability scoring | Assign confidence (e.g., by venue tier: ICML=A, workshop=C) | Low |
| Competing hypothesis agent | Given conflicting benchmark results, generate alternative explanations | Medium |
| Temporal graph snapshots | Point-in-time graph queries ("what did the graph look like in 2022?") | Medium |
| Multimodal ingestion | Parse figures/tables from PDFs, not just abstracts | High |
| Real-time streaming | Live arXiv feed → auto-ingest new papers | Medium |
| Access control layer | Role-based visibility on nodes/edges | Low (Neo4j Enterprise) |

---

## Appendix A: PwC Dataset Statistics (Approximate)

| Entity | Estimated Count |
|---|---|
| Papers | ~300,000+ |
| Authors | ~500,000+ (pre-dedup) |
| Methods | ~1,500+ |
| Tasks | ~3,000+ |
| Datasets | ~6,000+ |
| Benchmark results | ~100,000+ |
| Code repositories | ~80,000+ |

Graph size estimate: ~1M nodes, ~5M edges (post-dedup). Well within Neo4j Community limits.

---

## Appendix B: Example Test Queries (Sample from §9.1)

### B.1 Single-hop

```
Q: "What methods does the paper 'Attention Is All You Need' use?"
Gold: Multi-Head Attention, Scaled Dot-Product Attention, Positional Encoding, Layer Normalization, ...
Type: factual_lookup
Strategy: GRAPH_ONLY
```

### B.2 Multi-hop (2 hops)

```
Q: "Which authors who published on Object Detection also have co-authors at Meta AI?"
Gold: [list of authors matching both conditions]
Type: multi_hop
Strategy: GRAPH_ONLY
Hops: Author → Paper → Task:Object Detection + Author → CO_AUTHORED → Author → Affiliation:Meta AI
```

### B.3 Multi-hop (3 hops)

```
Q: "Find methods that were first used in NLP papers but later adopted by
    authors at computer vision labs, and list the bridging papers."
Gold: [Attention, Transformer, etc. with specific bridging papers]
Type: multi_hop
Strategy: HYBRID_SEQUENTIAL
Hops: Method → Paper → Task:NLP (earliest) → Paper → Task:CV (later) → Author → Org
```

### B.4 Temporal

```
Q: "Show the quarterly growth of papers using Diffusion Models from 2020 to 2025"
Gold: [time series data showing exponential growth ~2022-2023]
Type: temporal_trend
Strategy: GRAPH_ONLY (aggregation query)
```

### B.5 Network

```
Q: "Who are the top 5 bridge authors connecting the Reinforcement Learning
    and Natural Language Processing research communities?"
Gold: [authors with high betweenness between RL and NLP communities]
Type: network_analysis
Strategy: GRAPH_ONLY (centrality query)
```

### B.6 Global Summary

```
Q: "What are the 5 most significant emerging research themes in 2024
    that were not prominent in 2022?"
Gold: [e.g., Mixture of Experts scaling, multimodal LLMs, RLHF/DPO, ...]
Type: global_summary
Strategy: HYBRID_PARALLEL (community summaries + temporal method trends)
```