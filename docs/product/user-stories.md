# User Stories — graphrag-neo4j

**Date:** 2026-03-02
**Format:** As a [persona], I want [goal], so that [benefit].

---

## Epic 1: Query the Knowledge Graph

### US-01 — Ask a natural language question
**As an** ML engineer,
**I want to** type a natural language question about ML research,
**so that** I can get a grounded answer without knowing Cypher or graph syntax.

**Acceptance Criteria:**
- [ ] Input field accepts free-form text
- [ ] Pressing Enter or clicking "Ask" submits the question
- [ ] Loading state is shown while processing
- [ ] Answer appears within 10 seconds
- [ ] Empty questions are rejected with a clear message

---

### US-02 — See example questions
**As a** new user,
**I want to** see pre-built example questions,
**so that** I can quickly understand what the system can do without having to think of a question myself.

**Acceptance Criteria:**
- [ ] At least 4 example questions are shown as clickable chips
- [ ] Clicking a chip populates the input AND submits automatically
- [ ] Examples cover different node types (Method, Dataset, Task, Paper)

---

### US-03 — Read a grounded answer
**As a** researcher,
**I want to** receive an answer that cites specific entities from the knowledge graph,
**so that** I can trust the answer is based on real data, not hallucination.

**Acceptance Criteria:**
- [ ] Answer text mentions specific entity names from the graph (e.g. "YOLO", "COCO")
- [ ] Answer reflects the retrieved subgraph, not general LLM knowledge
- [ ] Latency is displayed (e.g. "answered in 2.3s")

---

### US-04 — See which nodes seeded the retrieval
**As an** ML engineer,
**I want to** see which nodes were found via vector search,
**so that** I understand *what* the system matched before traversing the graph.

**Acceptance Criteria:**
- [ ] Seed nodes are listed or visually distinct in the graph (orange)
- [ ] Each seed node shows its label type (Method/Task/Dataset/Paper) and similarity score
- [ ] Seed node count matches configured `top_k` setting

---

## Epic 2: Explore the Graph Visually

### US-05 — See the retrieved subgraph
**As a** researcher,
**I want to** see the retrieved knowledge subgraph as an interactive visualization,
**so that** I understand the relationships the system used to generate its answer.

**Acceptance Criteria:**
- [ ] Force-directed graph renders within 2 seconds of receiving results
- [ ] All retrieved nodes are shown (seeds + traversed)
- [ ] All retrieved edges are shown with directional arrows
- [ ] Graph is interactive: user can drag nodes, zoom in/out, pan

---

### US-06 — Distinguish node types by color
**As a** user,
**I want to** see node types color-coded,
**so that** I can instantly understand what kind of entity each node is.

**Acceptance Criteria:**
- [ ] Paper nodes = blue
- [ ] Method nodes = green
- [ ] Task nodes = amber/yellow
- [ ] Dataset nodes = purple
- [ ] Seed nodes = orange (overrides type color)
- [ ] A legend is visible or nodes have tooltips with their type

---

### US-07 — Read edge relationship types
**As an** ML engineer,
**I want to** see relationship labels on graph edges,
**so that** I understand why nodes are connected (e.g. INTRODUCES vs APPLIED_ON).

**Acceptance Criteria:**
- [ ] Edge labels are visible on hover or always shown for close zoom levels
- [ ] Directed arrows show relationship direction
- [ ] Edge types include: INTRODUCES, APPLIED_ON, EVALUATED_ON, USED_FOR, VARIANT_OF

---

## Epic 3: Understand the Retrieval Mechanism

### US-08 — Inspect the generated Cypher query
**As a** technical user or developer,
**I want to** see the exact Cypher query that was used to retrieve the subgraph,
**so that** I understand how the system works and can trust its results.

**Acceptance Criteria:**
- [ ] A collapsible "Cypher query used" panel is shown below the graph
- [ ] Clicking it expands to show the full Cypher query in a code block
- [ ] Syntax is displayed in monospace font with code styling
- [ ] Panel is collapsed by default (doesn't dominate the UI)

---

## Epic 4: System Health & Exploration

### US-09 — Check system health
**As a** developer running the stack,
**I want** a health endpoint,
**so that** I can verify Neo4j and the backend are connected before querying.

**Acceptance Criteria:**
- [ ] `GET /api/health` returns `{"status": "ok", "neo4j": "connected"}`
- [ ] Returns `"neo4j": "error"` if Neo4j is unreachable
- [ ] HTTP 200 in both cases (status in body, not HTTP code)

---

### US-10 — Explore the graph schema
**As a** developer,
**I want to** query the available node labels and relationship types,
**so that** I can understand the graph structure without opening Neo4j Browser.

**Acceptance Criteria:**
- [ ] `GET /api/graph/schema` returns node labels and relationship types
- [ ] Response updates if schema changes (dynamic, not hardcoded)

---

### US-11 — One-command startup
**As a** technical evaluator or developer,
**I want to** start the full stack with a single command,
**so that** I can evaluate the project without complex manual setup.

**Acceptance Criteria:**
- [ ] `docker compose up --build` starts Neo4j, backend, and frontend
- [ ] Frontend is accessible at `http://localhost:3000` after startup
- [ ] Backend health check passes at `http://localhost:8000/api/health`
- [ ] Only prerequisite is Docker + an `OPENAI_API_KEY` in `.env`
