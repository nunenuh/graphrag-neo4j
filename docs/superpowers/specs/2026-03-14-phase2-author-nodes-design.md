# Phase 2: Author Nodes + Entity Resolution — Design Spec

**Date:** 2026-03-14
**Status:** Draft
**Scope:** Author-only (no Organization nodes)
**Approach:** Ingestion-Time ER (Approach 1)
**ER Threshold:** Conservative (>= 0.85 auto-merge, no review queue)

---

## 1. Goal

Add Author nodes and authorship relationships to the knowledge graph so the system can answer cross-domain, network-based queries that require traversing researcher connections — the class of queries that proves Graph RAG is better than traditional RAG.

**Target query:** "Which researchers who published object detection papers also contributed to NLP tasks?"

This query requires `Author -> Paper -> Task` traversal, which is impossible without Author nodes.

---

## 2. Data Model

### 2.1 New Node: Author

```
(:Author {
    uid: "author:<normalized_name_hash>",
    name: "Geoffrey Hinton",
    name_normalized: "geoffrey hinton",
    blocking_key: "hinton_g",
    aliases: '["G. Hinton", "G.E. Hinton", "Geoffrey E. Hinton"]',
    merged_into: null,
    created_at: datetime
})
```

- `uid`: deterministic hash from `name_normalized` to ensure idempotent MERGE
- `name`: display name — the most frequently occurring form across papers
- `name_normalized`: lowercase, diacritics removed, suffixes stripped
- `blocking_key`: `last_name + "_" + first_initial` — used for candidate grouping during ER
- `aliases`: JSON string array of all name variants seen
- `merged_into`: null for canonical authors; UID of canonical for merged duplicates

The Author neomodel already exists in code at `backend/src/graphrag_service/dbase/neo4j/models/nodes.py`. It also includes analytics properties (`community_id`, `pagerank`, `betweenness`, `h_index`) which are out of scope for Phase 2 but already defined in the model for Phase 3.

**Note:** Author is excluded from `ALL_NODE_MODELS` because it has no embedding/vector index. Author nodes are not vector-searchable — they are discovered only through graph traversal from seed Paper/Method/Task/Dataset nodes.

### 2.2 New Relationships

| Relationship | Direction | Properties | Source |
|---|---|---|---|
| `AUTHORED` | Author -> Paper | `order` (int, 0-based author position) | PwC `papers.json` `authors[]` |
| `CO_AUTHORED_WITH` | Author -> Author | `paper_count` (int, number of shared papers) | Derived from AUTHORED edges |

`AuthoredRel` model exists. `CoAuthoredWithRel` needs to be created.

### 2.3 Graph Shape After Phase 2

```
Author --AUTHORED--> Paper --EVALUATED_ON--> Dataset --USED_FOR--> Task
Author --CO_AUTHORED_WITH--> Author
```

This enables 3-hop paths: `Author -> Paper -> Dataset -> Task` and network queries via `CO_AUTHORED_WITH`.

---

## 3. Entity Resolution Pipeline

### 3.1 Overview

ER runs during ingestion, after Paper nodes are loaded. Three stages:

```
Extract -> Normalize + Block -> Score + Merge -> Create Nodes + Edges
```

### 3.2 Stage 1: Extract

- Source: `papers.json` `authors[]` array
- Existing parsers: `iter_authors()` and `iter_author_paper_edges()` in `library/parsers.py` (wrapped by `GraphService.load_authors()`)
- Output: list of `(raw_name, paper_uid, author_order)` tuples

### 3.3 Stage 2: Normalize + Block

- **Normalize** (existing `normalizer.py`):
  - Remove diacritics (e.g., "Muller" from "Muller")
  - Strip suffixes (Jr., Sr., III, etc.)
  - Detect CJK names (different name order)
  - Extract first/last/initials
- **Block** (existing `blocker.py`):
  - Compute `blocking_key = last_name + "_" + first_initial`
  - Group all authors with same blocking key into candidate blocks
  - Only compare within blocks (avoids O(n^2) full comparison)

### 3.4 Stage 3: Score + Merge

- **Score** (existing `scorer.py`):
  - Within each block, compute weighted composite similarity: `token_sort_ratio` (0.4) + `partial_ratio` (0.3) + `jaro_winkler` (0.3)
  - Threshold: >= 0.85 = auto-merge (same person) — matches existing `blocker.find_clusters()` default
  - Below 0.85 = different people (conservative, no review queue)
- **Merge** (new `merger.py`):
  - Leverage existing `_UnionFind` and `find_clusters()` from `blocker.py` for grouping
  - New logic: select canonical name from each cluster, collect aliases, generate deterministic uid
  - For each group: pick the most frequent name form as `name`, collect others as `aliases`
  - Generate deterministic `uid` from `name_normalized` of the canonical form

### 3.5 Stage 4: Create Nodes + Edges

- **Author nodes**: batch MERGE on `uid` (idempotent)
- **AUTHORED edges**: batch MERGE `(Author)-[:AUTHORED {order}]->(Paper)`
- **CO_AUTHORED_WITH edges**: for each paper, generate all author pairs; aggregate `paper_count` across papers; batch MERGE

### 3.6 Expected Scale

From ~5k papers:
- ~15k raw author name strings
- ~10-12k unique Author nodes after ER
- ~15k AUTHORED edges
- ~10-15k CO_AUTHORED_WITH edges (after deduplicating same-pair co-authorships across papers)

---

## 4. Ingestion Pipeline Integration

### 4.1 Updated Pipeline Steps

```
1. Parse + embed + upsert Paper nodes          (existing)
2. Parse + embed + upsert Method nodes         (existing)
3. Parse + embed + upsert Task nodes           (existing)
4. Parse + embed + upsert Dataset nodes        (existing)
5. Create USED_FOR + EVALUATED_ON rels         (existing)
6. Extract + normalize + block authors         (NEW)
7. Score + merge (entity resolution)           (NEW)
8. Create Author nodes + AUTHORED + CO_AUTHORED_WITH  (NEW)
```

### 4.2 CLI Commands

```bash
make ingest            # runs all steps 1-8
make ingest-authors    # runs only steps 6-8 (re-run ER independently)
```

### 4.3 Idempotency

All operations use Neo4j MERGE (not CREATE), so re-running is safe. If ingestion fails midway, re-run `make ingest-authors` to retry from step 6.

---

## 5. API Changes

No new endpoints. Existing endpoints updated to include Author data:

| Endpoint | Change |
|---|---|
| `GET /api/v1/graph/schema` | `node_labels` includes `"Author"` |
| `GET /api/v1/graph/explore` | Returns Author nodes + AUTHORED/CO_AUTHORED_WITH edges |
| `GET /api/v1/graph/stats` | Includes Author node count, AUTHORED/CO_AUTHORED_WITH edge counts |
| `GET /api/v1/graph/search?q=` | Searches Author nodes by name |
| `GET /api/v1/graph/nodes/{uid}` | Returns Author detail: aliases, papers, co-authors |
| `POST /api/v1/rag/query` | Traversal walks through Author nodes naturally |

---

## 6. RAG Pipeline Impact

The RAG pipeline (embed -> vector search -> traverse -> context -> generate) requires **no code changes**. The traversal already walks all relationship types from seed nodes. With Author nodes in the graph:

1. Vector search finds Papers/Tasks related to the query
2. Hop 1 discovers Authors via AUTHORED edges
3. Hop 2 discovers those Authors' other Papers/co-authors

The LLM receives Author names and paper connections in context, enabling cross-domain answers.

---

## 7. Frontend Changes

Minimal changes — the frontend is already dynamic with node types:

| Component | Change |
|---|---|
| `NodeLabel` type in `types/api.ts` | Add `"Author"` to union type |
| Graph visualization | Author nodes rendered in slate/gray (color already defined in `TraversalPath.tsx`) |
| Node detail panel | Show aliases, paper count, co-author list |
| Explore page | Authors appear in graph exploration |

---

## 8. What Already Exists vs What's New

| Component | Status | Location |
|---|---|---|
| Author neomodel | Exists | `dbase/neo4j/models/nodes.py` |
| AuthoredRel model | Exists | `dbase/neo4j/models/relationships.py` |
| `iter_authors()` parser | Exists, unused | `library/parsers.py` (wrapped by `GraphService.load_authors()`) |
| `iter_author_paper_edges()` parser | Exists, unused | `library/parsers.py` |
| Name normalizer | Exists, tested | `library/entity_resolution/normalizer.py` |
| Blocker | Exists, tested | `library/entity_resolution/blocker.py` |
| Scorer | Exists, tested | `library/entity_resolution/scorer.py` |
| Merger logic | **New** | `library/entity_resolution/merger.py` |
| CoAuthoredWithRel model | **New** | `dbase/neo4j/models/relationships.py` |
| Batch Author upsert | **New** | `modules/graph/repositories.py` |
| CO_AUTHORED_WITH derivation | **New** | `modules/graph/services.py` |
| CLI wiring (ingest-authors) | **New** | `modules/graph/handler.py` |
| Frontend NodeLabel update | **New** | `frontend/src/types/api.ts` |
| Author detail panel | **New** | `frontend/src/components/` |

Estimated: ~60% exists, ~40% new implementation.

---

## 9. Success Criteria

1. `make ingest` creates Author nodes with deduplicated names
2. Query "Which researchers who published object detection papers also contributed to NLP tasks?" returns a non-empty answer with specific author names
3. Graph visualization shows Author nodes connected to Papers
4. Explore page includes Author nodes
5. All existing tests pass + new tests for merger, batch upsert, CO_AUTHORED_WITH
6. 80%+ test coverage on new code

---

## 10. Out of Scope

- Organization nodes (PwC data lacks affiliation info)
- ORCID linking
- Method deduplication
- Human review queue for uncertain ER matches
- External API enrichment (Semantic Scholar, OpenAlex)
- Graph analytics (PageRank, community detection) — Phase 3
