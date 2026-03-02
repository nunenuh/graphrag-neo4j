# ADR-001: Use Neo4j as Unified Graph + Vector Store

**Date:** 2026-03-02
**Status:** Accepted
**Decider:** Lalu Erfandi Maula Yusnu

---

## Context

Graph RAG requires two retrieval mechanisms:
1. **Vector similarity search** — find nodes semantically similar to the query
2. **Graph traversal** — walk edges from those nodes to collect relational context

The question was: should these live in one database or two?

---

## Decision

Use **Neo4j 5.15** as the single database for both graph storage and vector similarity search.

Neo4j 5.11+ introduced a native vector index (`db.index.vector.queryNodes`) that stores embeddings as node properties and supports cosine similarity search. This means vector search and graph traversal can be combined in a **single Cypher query**.

---

## Alternatives Considered

### Option A: Neo4j (graph) + Pinecone or ChromaDB (vectors)
- Neo4j stores the graph structure
- Separate vector DB stores embeddings with node IDs as metadata
- Query flow: vector search → get IDs → Neo4j traversal from those IDs

**Pros:**
- Mature, battle-tested vector DB tooling
- Higher vector search throughput at scale

**Cons:**
- Two databases to manage, configure, and keep in sync
- Extra network hop between vector search and graph traversal
- Docker Compose complexity doubles
- Harder to explain in a portfolio context (more moving parts)

### Option B: Neo4j (graph) + LangChain GraphCypherQAChain (no embeddings)
- No vector search — LLM generates Cypher directly from the question
- Cypher is executed on Neo4j → results fed to LLM

**Pros:**
- Simple — no embedding calls needed
- LLM does all the retrieval reasoning

**Cons:**
- LLM-generated Cypher is fragile — fails on ambiguous or complex questions
- No semantic fuzzy matching — exact name matches only
- Harder to demonstrate "Graph RAG" as a concept (it's just Text2Cypher)

### Option C: Neo4j 5.15 native vector index (chosen)
- Embeddings stored as `float[]` properties on each node
- Neo4j vector index enables `CALL db.index.vector.queryNodes()`
- Vector search and Cypher traversal combined in one query

**Pros:**
- Single database, single connection, single Docker service
- Vector + graph in one Cypher query — architecturally elegant
- Shows Neo4j's modern capabilities (portfolio value)
- Simpler Docker Compose, simpler local dev

**Cons:**
- Requires Neo4j 5.11+ (community edition is free)
- Vector search performance lower than dedicated vector DBs at massive scale
- Embedding storage adds ~55 MB for 9k nodes (acceptable for MVP)

---

## Consequences

**Positive:**
- One database to maintain, back up, and reason about
- The "killer query" (vector search + traversal in one Cypher) becomes a portfolio talking point
- Setup is simpler — `docker compose up neo4j` and you have everything

**Negative:**
- At scale (>1M vectors), dedicated vector DB would outperform Neo4j's vector index
- If the project outgrows Neo4j, migrating embeddings requires re-ingestion

**Neutral:**
- Neo4j Community Edition is free but single-node only (fine for portfolio)

---

## References
- [Neo4j Vector Index documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [Neo4j 5.11 release notes](https://neo4j.com/release-notes/database/neo4j-5-11/)
