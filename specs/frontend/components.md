# Frontend Spec: Components

Directory: `frontend/src/components/`

See also: [[projects/graphrag-neo4j/docs/technical/adr/adr-003-shadcn-ui-over-alternatives]]

---

## Component Tree

```
App.tsx                          ← Root layout, state owner
├── StatusBadges.tsx             ← Live API + Neo4j health badges (polls /health/ping + /health/neo4j)
├── ThemeToggle.tsx              ← Dark/light mode toggle (localStorage-persisted)
├── ChatPanel.tsx                ← Question input + answer display + pipeline metadata
│   ├── ui/scroll-area.tsx       ← shadcn ScrollArea
│   └── ui/badge.tsx             ← shadcn Badge (seed node labels)
├── GraphViewer.tsx              ← Interactive force-directed graph (Neo4j NVL)
│   └── @neo4j-nvl/react         ← InteractiveNvlWrapper (canvas renderer, drag-enabled)
├── NodeDetailPanel.tsx          ← Slide-in panel showing full node metadata on click
│   ├── ui/badge.tsx             ← shadcn Badge
│   └── ui/scroll-area.tsx       ← shadcn ScrollArea
└── CypherPanel.tsx              ← Collapsible Cypher query display
    └── ui/collapsible.tsx       ← shadcn Collapsible
```

---

## Setup: shadcn/ui + Neo4j NVL

Install components before building:

```bash
cd frontend

# 1. Init shadcn (if not already done)
npx shadcn@latest init

# 2. Add all components used in this project
npx shadcn@latest add badge collapsible scroll-area

# 3. Install Neo4j NVL for graph visualization
npm install @neo4j-nvl/react @neo4j-nvl/interaction-handlers
```

Generated components live in `src/components/ui/`. **Do not edit these files** unless customizing a component permanently — treat them as owned source code, not library files.

---

## File Conventions

### File naming
- Components: `PascalCase.tsx` (`ChatPanel.tsx`, `GraphViewer.tsx`)
- Utilities/hooks: `camelCase.ts` (`useGraphDimensions.ts`)
- shadcn generated: match shadcn output (`button.tsx`, `badge.tsx`)

### Props interface
Every component defines its own props interface, co-located in the same file:

```typescript
// ✅ Correct: interface co-located with component
interface ChatPanelProps {
  onSubmit: (question: string) => void;
  answer: string;
  seedNodes: SeedNode[];
  isLoading: boolean;
}

export function ChatPanel({ onSubmit, answer, seedNodes, isLoading }: ChatPanelProps) {
  ...
}

// ❌ Wrong: unnamed inline prop type
export function ChatPanel({ onSubmit, answer }: { onSubmit: (q: string) => void; answer: string }) {
```

### Component size
- Max 200 lines per component file
- If a component grows past 150 lines, extract subcomponents

---

## `ChatPanel.tsx`

```typescript
/**
 * ChatPanel — question input + answer display + seed node badges + pipeline metadata
 *
 * Props:
 *   onSubmit          — called when user submits a question
 *   answer            — LLM-generated answer string (empty = no answer yet)
 *   seedNodes         — vector search results to show as badges
 *   isLoading         — true while query is in flight
 *   latencyMs         — total response time in ms
 *   metadata          — PipelineMetadata with model info, graph stats, step timings
 *   exampleQuestions  — 4 pre-seeded example questions
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2, Sparkles, Brain, GitBranch, FileText, Zap, ChevronDown, ChevronRight } from "lucide-react";
import type { SeedNode, PipelineMetadata } from "@/types/api";

interface ChatPanelProps {
  onSubmit: (question: string) => void;
  answer: string;
  seedNodes: SeedNode[];
  isLoading: boolean;
  latencyMs?: number;
  metadata: PipelineMetadata | null;
  exampleQuestions: string[];
}
```

**Sections in ChatPanel:**
1. **Example questions** — shown when no answer/loading, styled as subtle pill buttons
2. **Loading indicator** — centered spinner with "Searching knowledge graph..."
3. **Seed node badges** — colored by type with similarity score
4. **Answer** — in a ScrollArea with collapsible "Pipeline Details" below
5. **Pipeline Details** (collapsible) — shows:
   - LLM model/provider and embedding model/provider/dimension
   - Graph stats: seed count / top-K, total nodes, edges, traversal depth
   - Context length in characters
   - Per-step timing bars (embed, vector_search, traverse, build_context, generate)
6. **Input row** — custom inline input with embedded send button (not shadcn Button+Input)

**Badge colors per node type:**
| Label | Tailwind Classes |
|-------|-----------------|
| `Paper` | `bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20` |
| `Method` | `bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20` |
| `Task` | `bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20` |
| `Dataset` | `bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20` |

**Seed nodes in graph** (highlighted in `GraphViewer`): larger size (35px vs 22px) + `activated` state

---

## `GraphViewer.tsx`

```typescript
/**
 * GraphViewer — interactive force-directed graph using @neo4j-nvl/react
 *
 * Props:
 *   nodes        — all subgraph nodes
 *   edges        — all subgraph edges
 *   seedNodeIds  — IDs of seed nodes (rendered larger with activated state)
 *   onNodeSelect — callback when a node is clicked (null = canvas click)
 */

import { useRef, useMemo, useCallback } from "react";
import { InteractiveNvlWrapper } from "@neo4j-nvl/react";
import type { Node, Relationship, HitTargets } from "@neo4j-nvl/base";
import type { MouseEventCallbacks } from "@neo4j-nvl/react";
import type { GraphNode, GraphEdge } from "@/types/api";

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  seedNodeIds: Set<string>;
  onNodeSelect?: (nodeId: string | null) => void;
}

const NODE_COLORS: Record<string, string> = {
  Paper: "#3b82f6",    // blue-500
  Method: "#22c55e",   // green-500
  Task: "#a855f7",     // purple-500
  Dataset: "#f97316",  // orange-500
};

const DEFAULT_COLOR = "#64748b"; // slate-500 — fallback
const REL_COLOR = "rgba(148, 163, 184, 0.5)";
```

**GraphViewer Rules:**
- Uses `@neo4j-nvl/react` `InteractiveNvlWrapper` — supports drag, pan, zoom natively
- Nodes colored by **type** (Paper=blue, Method=green, Task=purple, Dataset=orange) — NOT by seed status
- Seed nodes differentiated by larger size (35px vs 22px) and `activated: true`
- Node ID prefers `uid` over `id`: `n.uid || n.id || ""`
- Canvas background: `hsl(var(--graph-bg))` — theme-aware (light/dark)
- NVL options: `layout: "forceDirected"`, `renderer: "canvas"`
- `onNodeClick` triggers `onNodeSelect(nodeId)` for NodeDetailPanel
- `onCanvasClick` triggers `onNodeSelect(null)` to deselect
- **Legend overlay** in bottom-left corner showing node type colors with counts and seed indicator

**NVL type interfaces:**
- `Node`: `{ id, color?, size?, caption?, activated?, selected?, pinned? }`
- `Relationship`: `{ id, from, to, caption?, color?, width? }`
- `NvlOptions`: `{ layout, initialZoom, renderer, styling: { defaultNodeColor, defaultRelationshipColor } }`
- `MouseEventCallbacks` imported from `@neo4j-nvl/react` (not `@neo4j-nvl/interaction-handlers`)

---

## `CypherPanel.tsx`

```typescript
/**
 * CypherPanel — collapsible panel showing the Cypher query used
 *
 * Props:
 *   cypher — the Cypher query string to display
 */

import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight } from "lucide-react";

interface CypherPanelProps {
  cypher: string;
}

export function CypherPanel({ cypher }: CypherPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!cypher) return null;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="flex items-center gap-1 text-xs">
          {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          Cypher Query
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="text-xs bg-muted rounded p-3 overflow-x-auto whitespace-pre-wrap font-mono">
          {cypher}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
}
```

---

## `NodeDetailPanel.tsx`

Slide-in panel overlaid on the graph area (absolute positioned). Shows full node metadata when a graph node is clicked.

**Props:**
- `node: GraphNode` — the selected node
- `edges: GraphEdge[]` — all subgraph edges (to find connected relationships)
- `allNodes: GraphNode[]` — all nodes (for relationship name lookups)
- `isSeed: boolean` — whether this node is a seed node
- `onClose: () => void` — close handler
- `onNodeSelect: (id: string) => void` — navigate to a connected node

**Sections:**
1. Header with type icon + name + label badge + seed indicator
2. Type-specific metadata fields:
   - Paper: title, abstract, year, URL (clickable)
   - Method: full_name, description
   - Task: area, description
   - Dataset: description, modalities
3. Extra properties (catch-all for any additional fields)
4. UID reference
5. Relationships (outgoing/incoming) — clickable to navigate to connected nodes

**Position:** `absolute top-3 right-3 bottom-3 w-72 z-20`

---

## `StatusBadges.tsx`

Live health check badges in the header. Polls backend API and Neo4j independently.

**Behavior:**
- On mount and every 30s, pings `GET /api/v1/health/ping` then `GET /api/v1/health/neo4j`
- If backend unreachable: both badges show red
- If backend ok but Neo4j down: API=green, Neo4j=red
- Neo4j badge shows latency on hover via `title` attribute

**States:** `loading` (yellow pulse), `healthy` (green), `unhealthy` (red)

---

## `ThemeToggle.tsx`

Dark/light mode toggle button with Sun/Moon icons.

**Behavior:**
- Reads initial theme from `localStorage.getItem("theme")` or system preference
- Toggles `dark` class on `document.documentElement`
- Persists choice to localStorage
- Flash prevention: inline script in `index.html` applies dark class before React hydrates

---

## shadcn/ui Component Usage Rules

| shadcn Component | Where Used | Key Props |
|-----------------|------------|-----------|
| `Badge` | Seed node labels, NodeDetailPanel type badge | Custom `className` for color override |
| `Collapsible` | Cypher panel | `open` + `onOpenChange` controlled |
| `ScrollArea` | Answer scroll, NodeDetailPanel content | Wrap scrollable areas |

**Other UI notes:**
- ChatPanel uses custom `<input>` + `<button>` (not shadcn Input/Button) for the embedded send button design
- GraphViewer uses `@neo4j-nvl/react` InteractiveNvlWrapper (not shadcn)
- StatusBadges and ThemeToggle use plain HTML elements + Tailwind + lucide-react icons

**Tailwind class rule**: Use Tailwind classes directly. Custom CSS is minimal — only for NVL container sizing, scrollbar styling, and CSS variable theming in `index.css`.

---

## TypeScript Rules

```typescript
// ✅ Always define prop interface
interface ComponentProps { ... }
export function Component(props: ComponentProps) { ... }

// ✅ Use type imports
import type { SeedNode, GraphNode } from "@/types/api";

// ❌ Never use `any` in component code
const handler = (e: any) => ...   // ❌

// ✅ Use proper event types
const handler = (e: React.ChangeEvent<HTMLInputElement>) => ...  // ✅

// ✅ Use Set for ID lookups (O(1))
seedNodeIds: Set<string>   // ✅ not string[]
```
