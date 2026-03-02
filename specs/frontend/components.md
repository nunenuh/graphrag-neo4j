# Frontend Spec: Components

Directory: `frontend/src/components/`

See also: [[projects/graphrag-neo4j/docs/technical/adr/adr-003-shadcn-ui-over-alternatives]]

---

## Component Tree

```
App.tsx                          ← Root layout, state owner
├── ChatPanel.tsx                ← Question input + answer display
│   ├── ui/input.tsx             ← shadcn Input
│   ├── ui/button.tsx            ← shadcn Button
│   ├── ui/scroll-area.tsx       ← shadcn ScrollArea
│   └── ui/badge.tsx             ← shadcn Badge (seed node labels)
├── GraphViewer.tsx              ← Force-directed graph canvas
│   ├── react-force-graph-2d     ← Canvas renderer
│   └── ui/tooltip.tsx           ← shadcn Tooltip (node hover)
└── CypherPanel.tsx              ← Collapsible Cypher query display
    └── ui/collapsible.tsx       ← shadcn Collapsible
```

---

## Setup: shadcn/ui

Install components before building:

```bash
cd frontend

# 1. Init shadcn (if not already done)
npx shadcn@latest init

# 2. Add all components used in this project
npx shadcn@latest add card button badge input
npx shadcn@latest add collapsible scroll-area tooltip
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
 * ChatPanel — question input + answer display + seed node badges
 *
 * Props:
 *   onSubmit    — called when user submits a question
 *   answer      — LLM-generated answer string (empty = no answer yet)
 *   seedNodes   — vector search results to show as badges
 *   isLoading   — true while query is in flight
 *   latencyMs   — response time in ms (shown when answer is available)
 *   exampleQuestions — 4 pre-seeded example questions
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { SeedNode } from "@/types/api";

interface ChatPanelProps {
  onSubmit: (question: string) => void;
  answer: string;
  seedNodes: SeedNode[];
  isLoading: boolean;
  latencyMs?: number;
  exampleQuestions: string[];
}

const BADGE_COLORS: Record<string, string> = {
  Paper: "bg-blue-100 text-blue-800",
  Method: "bg-green-100 text-green-800",
  Task: "bg-purple-100 text-purple-800",
  Dataset: "bg-orange-100 text-orange-800",
};

export function ChatPanel({
  onSubmit,
  answer,
  seedNodes,
  isLoading,
  latencyMs,
  exampleQuestions,
}: ChatPanelProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (q: string) => {
    if (!q.trim()) return;
    setQuestion(q);
    onSubmit(q.trim());
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Example questions */}
      <div className="flex flex-wrap gap-2">
        {exampleQuestions.map((eq) => (
          <Button
            key={eq}
            variant="outline"
            size="sm"
            onClick={() => handleSubmit(eq)}
            disabled={isLoading}
          >
            {eq}
          </Button>
        ))}
      </div>

      {/* Input row */}
      <div className="flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit(question)}
          placeholder="Ask a question about ML research..."
          disabled={isLoading}
        />
        <Button onClick={() => handleSubmit(question)} disabled={isLoading || !question.trim()}>
          {isLoading ? "Thinking..." : "Ask"}
        </Button>
      </div>

      {/* Seed node badges */}
      {seedNodes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-muted-foreground mr-1">Seed nodes:</span>
          {seedNodes.map((sn) => (
            <Badge
              key={sn.id}
              className={BADGE_COLORS[sn.label] ?? ""}
              variant="secondary"
            >
              {sn.name} ({sn.score.toFixed(2)})
            </Badge>
          ))}
        </div>
      )}

      {/* Answer */}
      {answer && (
        <ScrollArea className="flex-1 rounded-md border p-4">
          <p className="text-sm whitespace-pre-wrap">{answer}</p>
          {latencyMs !== undefined && (
            <p className="text-xs text-muted-foreground mt-2">{latencyMs}ms</p>
          )}
        </ScrollArea>
      )}
    </div>
  );
}
```

**Badge colors per node type:**
| Label | Color |
|-------|-------|
| `Paper` | Blue |
| `Method` | Green |
| `Task` | Purple |
| `Dataset` | Orange |

**Seed nodes in graph** (highlighted separately in `GraphViewer`): orange border/glow

---

## `GraphViewer.tsx`

```typescript
/**
 * GraphViewer — force-directed graph visualization using react-force-graph-2d
 *
 * Props:
 *   nodes        — all subgraph nodes
 *   edges        — all subgraph edges
 *   seedNodeIds  — IDs of seed nodes (rendered with orange highlight)
 */

import { useRef, useEffect, useState, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphNode, GraphEdge } from "@/types/api";

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  seedNodeIds: Set<string>;
}

const NODE_COLORS: Record<string, string> = {
  Paper: "#3b82f6",    // blue-500
  Method: "#22c55e",   // green-500
  Task: "#a855f7",     // purple-500
  Dataset: "#f97316",  // orange-500
};

const SEED_COLOR = "#f97316"; // orange — seed node highlight
const DEFAULT_COLOR = "#94a3b8"; // slate-400 — fallback

export function GraphViewer({ nodes, edges, seedNodeIds }: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  // Measure container on mount and resize
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Transform to react-force-graph-2d format
  const graphData = {
    nodes: nodes.map((n) => ({
      id: n.id,
      label: n.label,
      name: n.name || n.title || n.id,
      isSeed: seedNodeIds.has(n.id),
    })),
    links: edges.map((e) => ({
      source: e.from_id,
      target: e.to_id,
      type: e.type,
    })),
  };

  const nodeColor = useCallback((node: any) => {
    if (node.isSeed) return SEED_COLOR;
    return NODE_COLORS[node.label] ?? DEFAULT_COLOR;
  }, []);

  const nodeLabel = useCallback((node: any) => {
    return `${node.label}: ${node.name}`;
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeColor={nodeColor}
        nodeLabel={nodeLabel}
        nodeRelSize={5}
        linkLabel={(link: any) => link.type}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        backgroundColor="#0f172a"  // slate-900 (dark background)
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          // Draw seed node ring
          if (node.isSeed) {
            ctx.beginPath();
            ctx.arc(node.x!, node.y!, 7, 0, 2 * Math.PI);
            ctx.strokeStyle = SEED_COLOR;
            ctx.lineWidth = 2;
            ctx.stroke();
          }
          // Draw node label when zoomed in
          if (globalScale >= 1.5) {
            const label = node.name;
            ctx.font = `${10 / globalScale}px Sans-Serif`;
            ctx.fillStyle = "#ffffff";
            ctx.textAlign = "center";
            ctx.fillText(label, node.x!, node.y! + 10);
          }
        }}
      />
    </div>
  );
}
```

**GraphViewer Rules:**
- Use `ResizeObserver` (not hardcoded dimensions) — the container may resize
- Seed nodes get an orange ring highlight (`nodeCanvasObject`)
- Node labels render only when `globalScale >= 1.5` (avoid clutter)
- Canvas background: `#0f172a` (dark) — contrasts with colored nodes
- `react-force-graph-2d` is canvas-based — no CSS interference from shadcn/ui

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

## shadcn/ui Component Usage Rules

| shadcn Component | Where Used | Key Props |
|-----------------|------------|-----------|
| `Card` | Panel containers in `App.tsx` | `className="h-full"` for full-height |
| `Input` | Question input in `ChatPanel` | `onKeyDown` for Enter key submit |
| `Button` | Submit + example questions | `disabled={isLoading}` |
| `Badge` | Seed node type labels | Custom `className` for color override |
| `Collapsible` | Cypher panel | `open` + `onOpenChange` controlled |
| `ScrollArea` | Answer scroll | Wrap answer text |
| `Tooltip` | Node hover in graph | Wrap `ForceGraph2D` container |

**Tailwind class rule**: Use Tailwind classes directly. Do not write custom CSS files unless absolutely necessary (shadcn's CSS variables handle theming).

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
