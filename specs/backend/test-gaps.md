# Unit Test Gap Analysis — Edge & Corner Cases

Current state: **143 unit tests passing, 74% coverage**.
Most tests cover the happy path. Below are the missing edge cases, corner cases, and boundary tests grouped by module.

---

## 1. `core/auth` — API Key Validation

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Near-miss key (off by one char: `test-api-kex`) | edge | Verifies timing-safe compare rejects similar keys |
| 2 | Key with leading/trailing whitespace (`" test-api-key "`) | edge | Whitespace padding should not bypass auth |
| 3 | Key with unicode zero-width space (`test-api-key\u200b`) | corner | Invisible chars must not bypass compare |
| 4 | Very long key (10k chars) | boundary | No crash or slow comparison on oversized input |
| 5 | Case-flipped key (`TEST-API-KEY`) | edge | Confirms case-sensitive matching |
| 6 | Substring of valid key (`test-api`) | edge | Partial key must not match |
| 7 | Superset of valid key (`test-api-key-extra`) | edge | Extended key must not match |

---

## 2. `core/config` — Settings & Parsing

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `ALLOWED_ORIGINS_STR` with trailing comma (`"http://a.com,"`) | edge | Should not produce empty-string origin |
| 2 | `ALLOWED_ORIGINS_STR` with only commas (`",,,,"`) | corner | Should return empty list |
| 3 | `ALLOWED_ORIGINS_STR` with single origin (no comma) | edge | Single-item parse |
| 4 | `ALLOWED_ORIGINS_STR` with whitespace-only entries (`"  , ,  "`) | corner | Should filter out blanks |
| 5 | Env vars override .env file values | edge | Confirm pydantic-settings precedence |
| 6 | `APP_PORT` is int not string | boundary | Type coercion from env |
| 7 | `EMBEDDING_DIM` must be positive | boundary | Validate constraint |

---

## 3. `core/dependencies` — Neo4j Singleton

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Double close (close → close) — no error | corner | Idempotent shutdown |
| 2 | Get → close → get creates new instance | edge | Re-creation after teardown |
| 3 | Constructor raises — exception propagates | error | Startup failure path |

---

## 4. `modules/graph/repositories` — Validation & Queries

### `_validate_label`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Cypher injection attempt (`"Paper} DETACH DELETE"`) | security | Injection prevention |
| 2 | Empty string label | boundary | Rejects empty |
| 3 | Label with special chars (`"Paper!"`, `"Pa per"`) | edge | Only exact allowlist matches |

### `_validate_rel_type`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Cypher injection in rel type (`"REL]->(x) DELETE"`) | security | Injection prevention |
| 2 | Lowercase valid name (`"used_for"`) | edge | Regex requires uppercase |
| 3 | Name with spaces (`"USED FOR"`) | edge | Spaces rejected |
| 4 | Single character `"A"` vs `"a"` | boundary | Uppercase-only rule |

### `GraphExploreRepository`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `explore` deduplicates when same node appears as both `a` and `b` | corner | Node dict keyed by uid |
| 2 | `explore` filters out `embedding` key from node properties | edge | Embedding excluded from output |
| 3 | `get_stats` with empty database (all counts = 0) | boundary | Zero totals |
| 4 | `get_stats` node count query fails → `RepositoryException` | error | Error path |
| 5 | `get_stats` edge count query fails → `RepositoryException` | error | Separate error from node counts |
| 6 | `get_stats` with no relationships in DB | edge | Empty rel types list |
| 7 | `get_node_by_uid` with `n = None` in row (node deleted between match and return) | corner | Returns None |
| 8 | `get_node_by_uid` db error → `RepositoryException` | error | Exception chaining |
| 9 | `get_node_by_uid` filters out null outgoing/incoming entries | edge | Entries with `to=None` or `type=None` excluded |
| 10 | `search_nodes` empty result set | boundary | Returns `[]` |
| 11 | `search_nodes` node has `embedding` key — excluded from properties | edge | Privacy/size |

### `SchemaRepository`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `get_relationship_types` db error → `RepositoryException` | error | Exception chaining |

### `NodeRepository`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `upsert_batch` with empty batch (no nodes) | boundary | No-op, no error |
| 2 | `upsert_batch` merges embedding into records correctly | edge | Zip alignment |
| 3 | `merge_used_for` uses parameterized queries (no injection) | security | Params not interpolated |

---

## 5. `modules/graph/handler` — API Endpoints

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `GET /explore` — default limit (no `?limit=` param) returns 200 | edge | Default 50 |
| 2 | `GET /explore` — db error returns 503 | error | RepositoryException path |
| 3 | `GET /explore?limit=-1` — returns 422 | boundary | Negative limit |
| 4 | `GET /explore?limit=abc` — returns 422 | boundary | Non-integer limit |
| 5 | `GET /stats` — db error returns 503 | error | RepositoryException path |
| 6 | `GET /nodes/{uid}` — db error returns 503 | error | RepositoryException path |
| 7 | `GET /search?q=test` — db error returns 503 | error | RepositoryException path |
| 8 | `GET /search?q=test&limit=0` — returns 422 | boundary | Zero limit |
| 9 | `GET /search?q=test&limit=101` — returns 422 | boundary | Over max limit |
| 10 | `GET /search?q=a` — min length 1 is accepted | boundary | Min length |
| 11 | 503 response body includes `timestamp` and `error` keys | edge | Error envelope format |
| 12 | 503 response body hides message when `APP_DEBUG=false` | security | Error sanitization |

---

## 6. `modules/rag/repositories` — Vector Search & Traversal

### `VectorSearchRepository`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `search` uses correct index name format (`vector_index_{label}_embedding`) | edge | Index naming convention |
| 2 | `search` node without `name` falls back to `title` | edge | Name resolution fallback |
| 3 | `search` node without `name` or `title` returns empty name | corner | Double fallback |
| 4 | `search` filters out `embedding` from properties | edge | Embedding excluded |
| 5 | `search_all` with `k` larger than total results | boundary | Returns all available |
| 6 | `search_all` one label search fails — entire call fails | error | No partial results |

### `TraversalRepository`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `traverse` with empty `node_ids` list | boundary | Cypher handles empty `$ids` |
| 2 | `traverse` deduplicates edges (same edge in `e1` and `e2`) | corner | Duplicate prevention |
| 3 | `traverse` edge missing `props` key uses empty dict | edge | Optional properties |
| 4 | `traverse` multiple seed rows merge correctly | edge | Multi-row aggregation |

---

## 7. `modules/rag/handler` — RAG Query Endpoint

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Whitespace-only question (`"   "`) — returns 422 | edge | `min_length=1` after strip? No, Pydantic counts spaces |
| 2 | Non-JSON request body — returns 422 | boundary | Malformed request |
| 3 | Wrong content type (form-encoded) — returns 422 | boundary | Content negotiation |
| 4 | Extra fields in request body are ignored | edge | Pydantic model ignores extras |
| 5 | Question at exact max length (2000 chars) — returns 200 | boundary | Boundary value |
| 6 | 503 error body includes `timestamp` field | edge | Error envelope |
| 7 | 500 error body hides real message (says "An unexpected error occurred") | security | No leak in non-debug |
| 8 | Empty subgraph (no seed_nodes, no edges) — returns 200 with empty lists | edge | Pipeline returns no results |

---

## 8. `modules/health` — Health Checks

### Services

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `check_neo4j` response time is non-negative float | boundary | Timing math |
| 2 | `check_neo4j` `verify_connection` raises (not returns False) | edge | Different from unhealthy |
| 3 | `get_health_service` returns singleton | edge | Global state |
| 4 | `get_basic_health` uptime increases over time | edge | Monotonic clock |

### Handler

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `GET /status` does not require auth | edge | Health is public |
| 2 | `GET /status` response includes `version` field matching settings | edge | Version string |
| 3 | `GET /status` 503 error body includes `timestamp` | error | Error envelope |
| 4 | `GET /ping` response `timestamp` is valid ISO format | edge | Parseable timestamp |

---

## 9. `library/parsers` — Data Parsing

### `iter_papers`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Empty input list `[]` | boundary | Returns empty iterator |
| 2 | Paper with `None` title — skipped | corner | Falsy title check |
| 3 | Paper with `None` abstract — skipped | corner | Falsy abstract check |
| 4 | Paper with empty string title `""` — skipped | edge | Empty != present |
| 5 | Paper missing `paper_url` falls back to `id` field | edge | UID fallback chain |
| 6 | Paper missing both `paper_url` and `id` — uid is `""` | corner | Double fallback |
| 7 | Paper missing `published` — year is `""` | edge | Safe slicing on empty |
| 8 | Paper with short `published` (e.g., `"20"`) — year is `"20"` | corner | Slice `[:4]` on short string |
| 9 | Unicode characters in title/abstract preserved | edge | i18n support |
| 10 | Mixed valid and invalid papers — only valid ones yielded | edge | Filtering mid-stream |
| 11 | `max_papers` larger than data length — returns all | boundary | No index error |

### `iter_methods`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Empty input list | boundary | Empty iterator |
| 2 | Method with `None` name — skipped | corner | Falsy check |
| 3 | Method with `None` description — uses `""` | edge | Null coalescing |
| 4 | Method with `None` full_name — falls back to name | edge | Null coalescing |
| 5 | Description truncated at 2000 chars | boundary | Length limit |

### `iter_tasks`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Empty input list | boundary | Empty iterator |
| 2 | Task with `None` area — uses `""` | edge | Null coalescing |
| 3 | Task with `None` description — uses `""` | edge | Null coalescing |

### `iter_datasets`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Empty input list | boundary | Empty iterator |
| 2 | Dataset with `None` modalities — uses `""` | corner | `None` → `[]` join |
| 3 | Dataset with single modality — no comma | edge | Join behavior |
| 4 | Dataset with `None` description — uses `""` | edge | Null coalescing |
| 5 | Description truncated at 1000 chars | boundary | Length limit |

---

## 10. `library/llm/embeddings`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `embed_text(None)` — returns zero vector (or raises) | corner | None input guard |
| 2 | `embed_text` with very long text (100k chars) — no crash | boundary | Large input |
| 3 | `embed_batch([])` — returns `[]` | boundary | Empty batch |
| 4 | `embed_batch` with all whitespace-only strings | corner | All replaced with `"empty"` |
| 5 | `embed_batch` newlines in batch items replaced with spaces | edge | Sanitization |
| 6 | `embed_batch` partial failure (first batch ok, second fails) — fallback on second only | edge | Graceful degradation |
| 7 | `embed_batch` with exactly `batch_size` items — single batch | boundary | No off-by-one |

---

## 11. `library/llm/chat`

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `generate` with empty context `""` | edge | LLM still called |
| 2 | `generate` with empty question `""` | edge | LLM still called |
| 3 | `generate` response content is non-string (e.g., int) — cast to str | corner | `str(response.content)` |
| 4 | `generate` with very long context (100k chars) — no crash | boundary | Large prompt |
| 5 | `generate` uses default `SYSTEM_PROMPT` when not overridden | edge | Default behavior |
| 6 | `generate` exception preserves original error in chain (`from e`) | error | Exception chaining |

---

## 12. `library/generator` — Context Building

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | Seed node with missing `label` key — defaults to `"Node"` | corner | `.get("label", "Node")` |
| 2 | Seed node with missing `name` key — defaults to `""` | corner | `.get("name", "")` |
| 3 | Seed node with missing `score` key — defaults to `0.0` | corner | `.get("score", 0.0)` |
| 4 | Edge with `properties=None` — treated as falsy, no props shown | edge | Truthy check |
| 5 | Edge with `properties={}` — treated as falsy, no props shown | edge | Empty dict is falsy |
| 6 | Exactly 30 edges — all shown | boundary | Boundary of `[:30]` |
| 7 | Single seed node, single edge — minimal output format | edge | Smallest valid case |

---

## 13. `library/graph/rag_pipeline` — LangGraph Pipeline

| # | Test Case | Type | Why |
|---|-----------|------|-----|
| 1 | `embed_fn` raises exception — pipeline propagates it | error | No silent swallow |
| 2 | `search_fn` raises exception — pipeline propagates | error | Error propagation |
| 3 | `generate_fn` raises exception — pipeline propagates | error | Error propagation |
| 4 | `top_k` parameter is correctly passed to `search_fn` | edge | Param forwarding |
| 5 | Multiple seed nodes — all IDs passed to `traverse_fn` | edge | Multi-seed traversal |
| 6 | Pipeline state contains all expected keys after completion | edge | State schema validation |
| 7 | `build_rag_graph` returns compilable graph (`.compile()` succeeds) | edge | Graph validity |

---

## Summary

| Category | Existing Tests | Missing Tests | Total Needed |
|----------|---------------|---------------|-------------|
| Auth | 4 | 7 | 11 |
| Config | 10 | 7 | 17 |
| Dependencies | 4 | 3 | 7 |
| Graph Repos | 14 | 14 | 28 |
| Graph Handler | 11 | 12 | 23 |
| RAG Repos | 8 | 10 | 18 |
| RAG Handler | 7 | 8 | 15 |
| Health | 9 | 8 | 17 |
| Parsers | 15 | 20 | 35 |
| Embeddings | 9 | 7 | 16 |
| Chat | 4 | 6 | 10 |
| Generator | 6 | 7 | 13 |
| Pipeline | 3 | 7 | 10 |
| **Total** | **104** | **116** | **220** |

Priority order for implementation:
1. **Security** — injection attempts, error message leaks, auth edge cases
2. **Error paths** — all RepositoryException/ServiceException propagation
3. **Boundary** — empty inputs, zero counts, max lengths, off-by-one
4. **Corner** — None values, missing keys, deduplication, fallback chains
