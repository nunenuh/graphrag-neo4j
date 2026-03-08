# Frontend v2 — Product Requirements Document

**Version:** 2.0
**Date:** 2026-03-09
**Status:** Draft
**Owner:** Lalu Erfandi Maula Yusnu

---

## 1. Motivation

The frontend v1 is a single-page query demo: type a question, see an answer + graph. But the backend now has 5 complete phases of functionality — entity resolution, graph analytics, agentic RAG pipeline, and evaluation framework — all invisible to the user.

This app is meant to **showcase the Graph RAG system's capabilities**, not just serve as a query box. Users should see:

- **How well** the system performs (evaluation metrics, baseline comparisons)
- **What's inside** the knowledge graph (exploration, statistics, schema)
- **How the graph is structured** (communities, centrality, trends)
- **How the pipeline works** (query classification, routing, provenance)
- **Who the researchers are** (author network, entity resolution)

---

## 2. Design Principles

1. **Multi-page app with navigation** — Replace monolithic single-page with route-based pages
2. **Backend-first** — Every frontend feature maps to an existing API endpoint
3. **Data-rich** — Show numbers, charts, tables — not just text answers
4. **Progressive disclosure** — Summary first, drill-down on click
5. **Same tech stack** — React + Vite + TypeScript + Tailwind + shadcn/ui (no new frameworks)

---

## 3. Information Architecture

```
┌─ Navigation Bar ──────────────────────────────────────────────┐
│  graphrag-neo4j  │  Dashboard │ Query │ Explore │ Analytics │ Evaluation │ [Theme] [Status] │
└──────────────────────────────────────────────────────────────┘

Pages:
  /                → Dashboard (overview + stats)
  /query           → Query interface (existing, enhanced)
  /explore         → Knowledge graph explorer
  /analytics       → Graph analytics (communities, trends, centrality)
  /evaluation      → Evaluation dashboard (metrics, baselines, queries)
```

---

## 4. Pages

### 4.1 Dashboard (`/`)

**Purpose:** System overview — what's in the graph, is it healthy, what can it do.

**Data sources:**
- `GET /api/v1/health/status` — system health + uptime
- `GET /api/v1/graph/stats` — node/edge counts by type
- `GET /api/v1/graph/schema` — node labels + relationship types

**Components:**

| Component | Description |
|-----------|-------------|
| `StatsCards` | 4 metric cards: Papers, Methods, Tasks, Datasets (counts from `/graph/stats`) |
| `RelationshipSummary` | Table/list of relationship types with counts |
| `SchemaViewer` | Visual schema: node types + their relationships (from `/graph/schema`) |
| `SystemHealth` | Expanded health: API status, Neo4j status, response time, uptime, version |
| `QuickActions` | Buttons to jump to Query, Explore, Analytics, Evaluation |

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  Knowledge Graph Overview                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│  │Papers│ │Methods│ │Tasks │ │Datasets│           │
│  │5,247 │ │1,832 │ │  743 │ │  621  │            │
│  └──────┘ └──────┘ └──────┘ └──────┘             │
│                                                   │
│  ┌─ Schema ──────────┐  ┌─ System Health ────────┐│
│  │ Paper ─USES→ Method│  │ API: ● healthy (23ms) ││
│  │ Paper ─EVAL→ Dataset│  │ Neo4j: ● healthy (5ms)││
│  │ Method ─FOR→ Task  │  │ Uptime: 2h 34m        ││
│  │ ...                │  │ Version: 1.0.0         ││
│  └────────────────────┘  └────────────────────────┘│
│                                                   │
│  ┌─ Quick Actions ───────────────────────────────┐│
│  │ [Ask a Question] [Explore Graph] [Analytics]  ││
│  │ [Run Evaluation]                              ││
│  └────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

---

### 4.2 Query (`/query`)

**Purpose:** Ask natural language questions — the existing core feature, enhanced with Phase 4 pipeline transparency.

**Data sources:**
- `POST /api/v1/rag/query` — existing endpoint

**Enhancements over v1:**

| Enhancement | Detail |
|-------------|--------|
| Query type badge | Show classified type (FACTUAL_LOOKUP, COMPARISON, etc.) above the answer |
| Retrieval strategy indicator | Show which strategy was used (GRAPH_ONLY, VECTOR_ONLY, HYBRID_PARALLEL, HYBRID_SEQUENTIAL) |
| Provenance score bar | Visual bar (0-100%) showing answer groundedness |
| Unsupported claims | Warning list of claims not backed by context |
| Enhanced step timings | Show new pipeline steps: analyze, embed, retrieve, context, generate, validate |

**New PipelineMetadata fields to display:**
```typescript
// Already in API response from Phase 4, not yet shown in frontend
query_type: string;              // "FACTUAL_LOOKUP", "COMPARISON", etc.
retrieval_strategy: string;      // "GRAPH_ONLY", "HYBRID_PARALLEL", etc.
provenance_score: number | null; // 0.0 - 1.0
unsupported_claims: string[];    // Claims not grounded in context
```

**Layout:** Same two-panel layout as v1 (ChatPanel | GraphViewer), with new info badges in the answer area.

---

### 4.3 Explore (`/explore`)

**Purpose:** Browse and search the knowledge graph without asking a question. Discover what's inside.

**Data sources:**
- `GET /api/v1/graph/explore?limit=N` — random subgraph sample
- `GET /api/v1/graph/search?q=...&label=...&limit=N` — search by name
- `GET /api/v1/graph/nodes/{uid}` — single node detail with relationships
- `GET /api/v1/graph/schema` — available labels and relationship types

**Components:**

| Component | Description |
|-----------|-------------|
| `SearchBar` | Text search with label filter dropdown (Paper, Method, Task, Dataset, All) |
| `SearchResults` | List of matching nodes with name, label, snippet |
| `ExploreGraph` | Force-directed graph of explore results (reuse GraphViewer) |
| `NodeDetailPanel` | Same as v1, triggered by clicking a node in graph or search result |
| `ExploreControls` | Limit slider (10-200 nodes), refresh button, label filter checkboxes |

**Interactions:**
1. **On page load:** Fetch random subgraph via `/graph/explore?limit=50`
2. **Search:** Type in search bar → calls `/graph/search?q=...` → updates graph + result list
3. **Click node:** Opens NodeDetailPanel with full details from `/graph/nodes/{uid}`
4. **Click relationship in NodeDetailPanel:** Navigate to that connected node
5. **Refresh:** Fetch new random subgraph sample

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  [Search: ___________] [Label: All ▼] [🔄 Refresh] │
│                                                   │
│  ┌─ Results (left) ──┐  ┌─ Graph (right) ────────┐│
│  │ ResNet   [Method]  │  │                        ││
│  │ BERT     [Method]  │  │   Force-directed       ││
│  │ CIFAR-10 [Dataset] │  │   graph visualization  ││
│  │ ...                │  │                        ││
│  └────────────────────┘  └────────────────────────┘│
└──────────────────────────────────────────────────┘
```

---

### 4.4 Analytics (`/analytics`)

**Purpose:** Show graph analytics results — communities, trends, centrality. Demonstrates the system understands the structure of the knowledge graph.

**Data sources:**
- `POST /api/v1/analytics/run` — run analytics pipeline (communities, centrality, trends)
- `GET /api/v1/analytics/communities?limit=N` — community clusters
- `GET /api/v1/analytics/trends?type=Method&limit=N` — trending methods/tasks

**Components:**

| Component | Description |
|-----------|-------------|
| `AnalyticsHeader` | Title + "Run Analytics" button (triggers `POST /analytics/run`) |
| `CommunityList` | List of communities with member count, expandable to show members |
| `CommunityGraph` | Optional: color-coded graph visualization of community clusters |
| `TrendingChart` | Bar chart of top 10 trending Methods and Tasks by paper count |
| `CentralityTable` | Table of top nodes by PageRank / betweenness centrality |

**Sub-tabs:**
- **Communities** — Detected research clusters (Leiden algorithm)
- **Trends** — Most popular methods and tasks, sorted by usage count
- **Centrality** — Most influential nodes (PageRank, betweenness, h-index)

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  Graph Analytics              [Run Analytics 🔄]  │
│  ┌─ [Communities] [Trends] [Centrality] ─────────┐│
│                                                   │
│  Communities tab:                                  │
│  ┌─ Community 1 (42 members) ────────────────────┐│
│  │  ResNet, VGG, Inception, EfficientNet, ...    ││
│  ├─ Community 2 (38 members) ────────────────────┤│
│  │  BERT, GPT, T5, RoBERTa, ...                 ││
│  └────────────────────────────────────────────────┘│
│                                                   │
│  Trends tab:                                      │
│  ┌─ Top Methods ─────────┐ ┌─ Top Tasks ─────────┐│
│  │ Transformer ████████  │ │ Image Class. ████████││
│  │ Attention   ██████    │ │ Object Det.  ██████  ││
│  │ ResNet      █████     │ │ NLP         █████   ││
│  └────────────────────────┘ └────────────────────┘│
│                                                   │
│  Centrality tab:                                  │
│  │ Rank │ Node        │ PageRank │ Betweenness │  │
│  │  1   │ Transformer │ 0.0342   │ 0.1523      │  │
│  │  2   │ Attention   │ 0.0281   │ 0.1204      │  │
│  │  3   │ ResNet      │ 0.0256   │ 0.0987      │  │
└──────────────────────────────────────────────────┘
```

---

### 4.5 Evaluation (`/evaluation`)

**Purpose:** Show how well the Graph RAG system performs. Evaluation metrics, per-category breakdown, baseline comparisons, and per-query drill-down.

**Data sources:**
- New API endpoints needed (currently CLI-only):
  - `GET /api/v1/eval/queries` — list all 40 evaluation queries
  - `GET /api/v1/eval/queries?category=FACTUAL_LOOKUP` — filter by category
  - `POST /api/v1/eval/run` — run evaluation suite (optional: `category` param)
  - `GET /api/v1/eval/report/latest` — get latest evaluation report

**Components:**

| Component | Description |
|-----------|-------------|
| `EvalHeader` | Title + "Run Evaluation" button + category filter dropdown |
| `MetricCards` | Summary metric cards: Entity F1, Precision@10, Recall@10, Keyword Coverage, Provenance, Latency P95 |
| `CategoryBreakdown` | Per-category metric table or grouped bar chart (7 categories) |
| `BaselineComparison` | Table comparing 4 baselines: LLM-only, Plain RAG, Graph-only, Hybrid Full |
| `QueryDrillDown` | Expandable list of all 40 queries with: question, answer, expected entities, retrieved entities, metrics |
| `LatencyDistribution` | Latency P50/P95/P99 bar chart |

**Sub-tabs:**
- **Overview** — Summary metrics + category breakdown
- **Baselines** — Ablation study: 4 baselines side-by-side
- **Queries** — All 40 queries with drill-down to individual results

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  Evaluation Dashboard         [Run Evaluation 🔄] │
│  ┌─ [Overview] [Baselines] [Queries] ────────────┐│
│                                                   │
│  Overview tab:                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │F1    │ │P@10  │ │R@10  │ │KW Cov│ │Prov. │   │
│  │0.82  │ │0.75  │ │0.88  │ │0.71  │ │0.85  │   │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │
│                                                   │
│  ┌─ Per Category ────────────────────────────────┐│
│  │ Category       │ F1   │ P@10 │ R@10 │ Latency││
│  │ FACTUAL_LOOKUP │ 0.91 │ 0.85 │ 0.95 │  850ms ││
│  │ COMPARISON     │ 0.78 │ 0.70 │ 0.82 │ 1200ms ││
│  │ TEMPORAL       │ 0.65 │ 0.60 │ 0.72 │  950ms ││
│  │ NETWORK        │ 0.55 │ 0.48 │ 0.65 │ 2100ms ││
│  │ ...            │      │      │      │        ││
│  └────────────────────────────────────────────────┘│
│                                                   │
│  Baselines tab:                                   │
│  │ Metric    │ LLM-only │ Plain RAG │ Graph │ Hybrid ││
│  │ Entity F1 │   0.12   │   0.54    │ 0.71  │  0.82  ││
│  │ P@10      │   0.00   │   0.62    │ 0.58  │  0.75  ││
│  │ Latency   │  200ms   │   800ms   │ 650ms │ 1200ms ││
│                                                   │
│  Queries tab:                                     │
│  │ [FACTUAL] factual_001: What is YOLO?          │
│  │   Answer: YOLO is a real-time object...       │
│  │   Expected: [YOLO] | Retrieved: [YOLO, ...]   │
│  │   F1: 1.0 | P@10: 1.0 | Latency: 650ms       │
│  │ [COMPARISON] comparison_001: Compare BERT...   │
│  │   ...                                          │
└──────────────────────────────────────────────────┘
```

---

## 5. New API Endpoints Required

The following backend API endpoints need to be created to support the frontend:

| Method | Path | Purpose | Module |
|--------|------|---------|--------|
| `GET` | `/api/v1/eval/queries` | List evaluation queries (with optional `?category=` filter) | eval |
| `POST` | `/api/v1/eval/run` | Run evaluation suite (optional `?category=` param) | eval |
| `GET` | `/api/v1/eval/report/latest` | Get latest cached evaluation report | eval |

All other endpoints already exist in the backend.

---

## 6. Navigation & Routing

**Add React Router** (`react-router-dom`):

```
/               → DashboardPage
/query          → QueryPage (existing functionality, wrapped in page)
/explore        → ExplorePage
/analytics      → AnalyticsPage
/evaluation     → EvaluationPage
```

**Navigation bar** — persistent across all pages:
- Logo + app name (left)
- Page links: Dashboard, Query, Explore, Analytics, Evaluation (center)
- StatusBadges + ThemeToggle (right)

---

## 7. New TypeScript Types

```typescript
// types/api.ts — additions

// Extended PipelineMetadata (Phase 4 fields)
export interface PipelineMetadata {
  // ... existing fields ...
  query_type: string;
  retrieval_strategy: string;
  provenance_score: number | null;
  unsupported_claims: string[];
}

// GET /api/v1/graph/stats
export interface GraphStats {
  node_counts: Record<string, number>;  // { Paper: 5247, Method: 1832, ... }
  edge_counts: Record<string, number>;  // { USES: 12345, EVALUATED_ON: 6789, ... }
  total_nodes: number;
  total_edges: number;
}

// GET /api/v1/graph/search
export interface SearchResult {
  uid: string;
  name: string;
  label: NodeLabel;
  score?: number;
}

// GET /api/v1/analytics/communities
export interface Community {
  id: number;
  size: number;
  members: string[];            // node names
  label?: string;               // auto-generated label
}

// GET /api/v1/analytics/trends
export interface TrendItem {
  name: string;
  label: string;
  count: number;                // paper count using this method/task
}

// GET /api/v1/eval/queries
export interface EvalQueryInfo {
  id: string;
  category: string;
  question: string;
  expected_entities: string[];
  gold_answer_keywords: string[];
  difficulty: string;
}

// POST /api/v1/eval/run response
export interface EvalReport {
  system_name: string;
  total_queries: number;
  successful_queries: number;
  metrics_summary: Record<string, number>;
  metrics_by_category: Record<string, Record<string, number>>;
  failures: string[];
  results: EvalResultItem[];
  timestamp: string;
}

export interface EvalResultItem {
  query_id: string;
  category: string;
  question: string;
  answer: string;
  latency_ms: number;
  query_type: string;
  retrieval_strategy: string;
  provenance_score: number;
  metrics: Record<string, number>;
}
```

---

## 8. New API Client Functions

```typescript
// lib/api.ts — additions

export async function fetchGraphStats(): Promise<GraphStats> {
  return apiFetch<GraphStats>("/api/v1/graph/stats");
}

export async function searchNodes(q: string, label?: string, limit = 20): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (label) params.set("label", label);
  return apiFetch<SearchResult[]>(`/api/v1/graph/search?${params}`);
}

export async function fetchNodeDetail(uid: string): Promise<GraphNode> {
  return apiFetch<GraphNode>(`/api/v1/graph/nodes/${uid}`);
}

export async function runAnalytics(): Promise<void> {
  return apiFetch<void>("/api/v1/analytics/run", { method: "POST" });
}

export async function fetchCommunities(limit = 20): Promise<Community[]> {
  return apiFetch<Community[]>(`/api/v1/analytics/communities?limit=${limit}`);
}

export async function fetchTrends(type: "Method" | "Task" = "Method", limit = 10): Promise<TrendItem[]> {
  return apiFetch<TrendItem[]>(`/api/v1/analytics/trends?type=${type}&limit=${limit}`);
}

export async function fetchEvalQueries(category?: string): Promise<EvalQueryInfo[]> {
  const params = category ? `?category=${category}` : "";
  return apiFetch<EvalQueryInfo[]>(`/api/v1/eval/queries${params}`);
}

export async function runEvaluation(category?: string): Promise<EvalReport> {
  const params = category ? `?category=${category}` : "";
  return apiFetch<EvalReport>(`/api/v1/eval/run${params}`, { method: "POST" });
}

export async function fetchLatestReport(): Promise<EvalReport> {
  return apiFetch<EvalReport>("/api/v1/eval/report/latest");
}
```

---

## 9. New shadcn/ui Components Needed

```bash
npx shadcn@latest add tabs table progress separator dropdown-menu
```

| Component | Where Used |
|-----------|------------|
| `Tabs` | Analytics (Communities/Trends/Centrality), Evaluation (Overview/Baselines/Queries) |
| `Table` | Centrality table, baseline comparison, per-query results |
| `Progress` | Provenance score bar, metric visualizations |
| `Separator` | Section dividers |
| `DropdownMenu` | Label filter in Explore, category filter in Evaluation |

---

## 10. Implementation Phases

### Phase A: Foundation (routing + navigation + dashboard)
- Add `react-router-dom`
- Create `NavBar` component with page links
- Create `DashboardPage` with StatsCards + SchemaViewer + SystemHealth
- Wrap existing query UI in `QueryPage`
- Wire up routing in `App.tsx`

### Phase B: Explore page
- Create `ExplorePage` with SearchBar + ExploreGraph + NodeDetailPanel
- Wire up `/graph/explore`, `/graph/search`, `/graph/nodes/{uid}` APIs
- Reuse `GraphViewer` component

### Phase C: Query enhancements (Phase 4 pipeline transparency)
- Add query type badge and retrieval strategy indicator
- Add provenance score bar
- Add unsupported claims warning
- Update `PipelineMetadata` type with new fields

### Phase D: Analytics page
- Create `AnalyticsPage` with tabs
- Build `CommunityList`, `TrendingChart`, `CentralityTable`
- Wire up analytics API endpoints

### Phase E: Evaluation page + backend API endpoints
- Create 3 new backend API endpoints for evaluation
- Create `EvaluationPage` with tabs
- Build `MetricCards`, `CategoryBreakdown`, `BaselineComparison`, `QueryDrillDown`

---

## 11. File Structure (Target)

```
frontend/src/
├── App.tsx                      ← Router setup
├── main.tsx                     ← Entry point
├── types/
│   └── api.ts                   ← All TypeScript types (extended)
├── lib/
│   └── api.ts                   ← All API client functions (extended)
├── components/
│   ├── NavBar.tsx               ← NEW: Navigation bar
│   ├── ChatPanel.tsx            ← Existing (enhanced)
│   ├── GraphViewer.tsx          ← Existing (reused in Explore)
│   ├── NodeDetailPanel.tsx      ← Existing (reused in Explore)
│   ├── CypherPanel.tsx          ← Existing
│   ├── StatusBadges.tsx         ← Existing (moved to NavBar)
│   ├── ThemeToggle.tsx          ← Existing (moved to NavBar)
│   ├── StatsCards.tsx           ← NEW: Dashboard metric cards
│   ├── SchemaViewer.tsx         ← NEW: Schema visualization
│   ├── SearchBar.tsx            ← NEW: Explore search
│   ├── CommunityList.tsx        ← NEW: Community clusters
│   ├── TrendingChart.tsx        ← NEW: Trend bar charts
│   ├── CentralityTable.tsx      ← NEW: Centrality rankings
│   ├── MetricCards.tsx          ← NEW: Eval metric summary
│   ├── CategoryBreakdown.tsx   ← NEW: Per-category table
│   ├── BaselineComparison.tsx  ← NEW: Baseline comparison table
│   ├── QueryDrillDown.tsx      ← NEW: Per-query eval results
│   ├── ProvenanceBadge.tsx     ← NEW: Provenance score display
│   └── ui/                      ← shadcn/ui components
│       ├── badge.tsx
│       ├── button.tsx
│       ├── card.tsx
│       ├── collapsible.tsx
│       ├── dropdown-menu.tsx    ← NEW
│       ├── input.tsx
│       ├── progress.tsx         ← NEW
│       ├── scroll-area.tsx
│       ├── separator.tsx        ← NEW
│       ├── table.tsx            ← NEW
│       ├── tabs.tsx             ← NEW
│       └── tooltip.tsx
├── pages/
│   ├── DashboardPage.tsx        ← NEW
│   ├── QueryPage.tsx            ← NEW (wraps existing ChatPanel + GraphViewer)
│   ├── ExplorePage.tsx          ← NEW
│   ├── AnalyticsPage.tsx        ← NEW
│   └── EvaluationPage.tsx       ← NEW
└── hooks/
    ├── useGraphDimensions.ts    ← Existing
    └── usePolling.ts            ← NEW: generic polling hook for health/analytics
```

---

## 12. Out of Scope (v2)

- User authentication / login UI
- Persistent chat history / saved queries
- Real-time streaming responses (SSE/WebSocket)
- Mobile-responsive layout
- Export/download features (PDF/CSV)
- Admin panel for data management
- Author network visualization (defer to v3 with dedicated page)
