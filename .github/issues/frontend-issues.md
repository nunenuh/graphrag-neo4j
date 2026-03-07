# Frontend Issues — Phase 1 MVP

All issues target branch `dev`. Labels: `frontend`, `type: feature`, `priority: medium`, `phase: 1`.

---

## Issue 1: Frontend project scaffold and configuration

**Title**: Frontend project scaffold (Vite + React + TS + Tailwind + shadcn)

**Labels**: `frontend`, `type: chore`, `priority: high`, `phase: 1`

**Description**:

Set up the frontend project from scratch with all required tooling and configuration.

### Tasks

- [ ] Initialize Vite project with React + TypeScript template (`npm create vite@latest frontend -- --template react-ts`)
- [ ] Install and configure Tailwind CSS v3 with PostCSS
- [ ] Initialize shadcn/ui (`npx shadcn@latest init`) with dark theme defaults
- [ ] Add required shadcn components: `card`, `button`, `badge`, `input`, `collapsible`, `scroll-area`, `tooltip`
- [ ] Configure path alias `@/` in both `vite.config.ts` and `tsconfig.json`
- [ ] Create `frontend/.env.example` with `VITE_API_URL` and `VITE_API_KEY`
- [ ] Configure Vite dev proxy for `/api` → `http://localhost:8005` to avoid CORS in dev
- [ ] Install `react-force-graph-2d` and `lucide-react` dependencies
- [ ] Verify `npm run dev` starts cleanly on port 5173
- [ ] Verify `npm run build` produces a production bundle without errors

### Acceptance Criteria

- `npm run dev` starts Vite dev server on port 5173
- `npm run build` succeeds with zero errors
- `@/` path alias resolves correctly
- All shadcn components importable from `@/components/ui/`
- Dark theme applied by default (slate-950 background)

### Specs

- `specs/frontend/components.md` — shadcn setup section
- `specs/frontend/api-client.md` — vite.config.ts proxy, tsconfig paths
- `specs/conventions/repository-overview.md` — frontend/ structure

---

## Issue 2: TypeScript API types and API client layer

**Title**: API client layer: TypeScript types and fetch wrapper

**Labels**: `frontend`, `type: feature`, `priority: high`, `phase: 1`

**Description**:

Create the API client layer that all components will use to communicate with the backend. This includes TypeScript interfaces that mirror the backend API spec exactly, and a typed fetch wrapper with proper error handling.

### Tasks

- [ ] Create `src/types/api.ts` with all TypeScript interfaces:
  - `NodeLabel` type (`"Paper" | "Method" | "Task" | "Dataset"`)
  - `QueryRequest`, `QueryResponse`
  - `SeedNode`, `GraphNode`, `GraphEdge`
  - `SchemaResponse`, `ExploreResponse` (`ExploreNode`, `ExploreEdge`)
  - `HealthResponse`, `Neo4jStatus`
  - `ApiError` class extending `Error` with `statusCode` and `detail`
- [ ] Create `src/lib/api.ts` with:
  - `apiFetch<T>()` generic fetch wrapper with `X-API-Key` header from `VITE_API_KEY`
  - `queryGraph(question: string)` → `POST /api/v1/rag/query`
  - `fetchSchema()` → `GET /api/v1/graph/schema`
  - `exploreGraph(limit?)` → `GET /api/v1/graph/explore?limit=`
  - `checkHealth()` → `GET /api/v1/health/status`
  - Error handling: parse JSON error body, throw `ApiError` with status code
- [ ] Use `import.meta.env.VITE_API_URL` with fallback to `""` (proxy handles routing)
- [ ] Use `import.meta.env.VITE_API_KEY` for `X-API-Key` header
- [ ] Verify TypeScript strict mode has no type errors

### Acceptance Criteria

- All types match backend Pydantic models exactly (cross-reference `specs/backend/api.md`)
- `apiFetch` adds `Content-Type: application/json` and `X-API-Key` headers automatically
- `ApiError` thrown on non-2xx responses with parsed error detail
- Network errors (fetch fails) propagate as standard `TypeError`
- No `any` types anywhere in the API layer
- `npm run build` passes with strict TypeScript

### Specs

- `specs/frontend/api-client.md` — full implementation reference
- `specs/backend/api.md` — backend Pydantic models (source of truth for types)
- `docs/technical/api-spec.md` — endpoint contracts

---

## Issue 3: ChatPanel component

**Title**: ChatPanel: question input, example questions, and answer display

**Labels**: `frontend`, `type: feature`, `priority: medium`, `phase: 1`

**Description**:

Build the ChatPanel component — the left panel of the app where users type questions, click example questions, see seed node badges, and read LLM-generated answers.

### Tasks

- [ ] Create `src/components/ChatPanel.tsx` with props interface:
  - `onSubmit: (question: string) => void`
  - `answer: string`
  - `seedNodes: SeedNode[]`
  - `isLoading: boolean`
  - `latencyMs?: number`
  - `exampleQuestions: string[]`
- [ ] Implement question input with Enter key submit and Ask button
- [ ] Implement example question buttons (4 pre-seeded questions, clickable, disabled during loading)
- [ ] Implement seed node badges with color coding per node type:
  - Paper → blue, Method → green, Task → purple, Dataset → orange
- [ ] Implement answer display in `ScrollArea` with whitespace-pre-wrap
- [ ] Show latency in ms below the answer when available
- [ ] Show "Thinking..." on button during loading, disable input
- [ ] Guard against empty/whitespace-only submissions

### Acceptance Criteria

- Typing a question and pressing Enter calls `onSubmit` with trimmed text
- Clicking an example question fills input and triggers submission
- All inputs disabled while `isLoading` is true
- Seed node badges show correct color per label type
- Answer text renders with preserved line breaks
- Empty questions are ignored (no API call)
- Component is under 200 lines

### Specs

- `specs/frontend/components.md` — ChatPanel section with full implementation reference
- `specs/frontend/state.md` — prop types and state flow

---

## Issue 4: GraphViewer component

**Title**: GraphViewer: force-directed graph visualization

**Labels**: `frontend`, `type: feature`, `priority: medium`, `phase: 1`

**Description**:

Build the GraphViewer component — the right panel showing a force-directed graph of the knowledge subgraph returned by the RAG pipeline. Nodes are colored by type and seed nodes get a highlight ring.

### Tasks

- [ ] Create `src/components/GraphViewer.tsx` with props interface:
  - `nodes: GraphNode[]`
  - `edges: GraphEdge[]`
  - `seedNodeIds: Set<string>`
- [ ] Integrate `react-force-graph-2d` (canvas-based, not DOM)
- [ ] Use `ResizeObserver` to measure container and pass `width`/`height` to ForceGraph2D
- [ ] Transform `GraphNode[]` / `GraphEdge[]` into react-force-graph-2d format (`{ nodes, links }`)
- [ ] Color nodes by label type:
  - Paper → `#3b82f6` (blue-500)
  - Method → `#22c55e` (green-500)
  - Task → `#a855f7` (purple-500)
  - Dataset → `#f97316` (orange-500)
- [ ] Highlight seed nodes with orange ring via `nodeCanvasObject`
- [ ] Show node labels on hover via `nodeLabel` callback (`"Label: Name"`)
- [ ] Render node text labels only when `globalScale >= 1.5` (avoid clutter at zoom-out)
- [ ] Set dark canvas background (`#0f172a` slate-900)
- [ ] Show directional arrows on edges (`linkDirectionalArrowLength`, `linkDirectionalArrowRelPos`)
- [ ] Show relationship type on edge hover via `linkLabel`

### Acceptance Criteria

- Graph renders correctly with nodes and edges from RAG response
- Nodes are colored by type, seed nodes have orange ring
- Graph auto-resizes when container resizes (no hardcoded dimensions)
- Node labels appear on hover and when zoomed in
- Edge arrows point in correct direction
- Empty graph (no nodes) renders clean dark canvas without errors
- Component handles graph data updates without remounting canvas

### Specs

- `specs/frontend/components.md` — GraphViewer section with full implementation reference

---

## Issue 5: App shell, state management, CypherPanel, and integration

**Title**: App shell: state management, CypherPanel, and component integration

**Labels**: `frontend`, `type: feature`, `priority: medium`, `phase: 1`

**Description**:

Build the App root component that owns all query state, the CypherPanel component, and wire everything together into the three-panel layout. This is the integration issue that makes the app functional end-to-end.

### Tasks

- [ ] Create `src/components/CypherPanel.tsx`:
  - Collapsible panel showing the Cypher query used by the RAG pipeline
  - Uses shadcn `Collapsible` + `lucide-react` chevron icons
  - Returns `null` when cypher is empty string
- [ ] Implement `App.tsx` with full state management:
  - State: `isLoading`, `error`, `answer`, `seedNodes`, `nodes`, `edges`, `cypher`, `latencyMs`
  - `handleSubmit(question)` — clears stale state, calls `queryGraph()`, updates state
  - Derive `seedNodeIds` as `Set<string>` from `seedNodes` (not stored separately)
  - Error handling: distinguish `ApiError` (show detail) from network error (show "Is backend running?")
  - Always reset `isLoading` in `finally` block
- [ ] Implement three-panel grid layout:
  - Left: `Card` containing `ChatPanel`
  - Right top: `Card` containing `GraphViewer`
  - Right bottom: `Card` containing `CypherPanel` (only when cypher is non-empty)
  - Full viewport height: `h-[calc(100vh-120px)]`
  - Dark theme: `bg-slate-950`, `text-slate-100`
- [ ] Add header with project title and subtitle
- [ ] Add error banner (red) above layout when error state is set
- [ ] Wire 4 example questions as constants:
  - "What methods are used for object detection?"
  - "Which papers introduced transformer architectures?"
  - "What datasets are used to benchmark image classification?"
  - "How does BERT relate to other NLP methods?"
- [ ] Verify full flow: type question → loading state → answer + graph + cypher displayed
- [ ] Verify error flow: stop backend → submit question → error banner shown

### Acceptance Criteria

- Three-panel layout renders correctly at full viewport height
- Submitting a question shows loading state, then populates answer + graph + cypher
- Previous results are cleared before new query starts (no stale data flash)
- Error banner appears on API/network failure with appropriate message
- CypherPanel only visible when a query has been made
- CypherPanel is collapsible (starts collapsed)
- State never gets stuck in loading (finally block always runs)
- Dark theme consistent across all panels
- App works end-to-end with running backend

### Specs

- `specs/frontend/state.md` — full App.tsx implementation reference
- `specs/frontend/components.md` — CypherPanel section
- `specs/frontend/api-client.md` — error handling patterns

---

## Issue Order (dependency chain)

```
#1 (scaffold)
  └─→ #2 (types + API client)
        └─→ #3 (ChatPanel)       ← can be parallel with #5
        └─→ #5 (GraphViewer)     ← can be parallel with #3
              └─→ #4 (App shell + CypherPanel + integration)
```

Issues #3 and #5 can be worked in parallel after #2 is done.
Issue #4 depends on all previous issues.
