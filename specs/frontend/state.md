# Frontend Spec: State Management

File: `frontend/src/App.tsx` (root state owner)

See also: [[projects/graphrag-neo4j/specs/frontend/api-client]] · [[projects/graphrag-neo4j/specs/frontend/components]]

---

## State Philosophy

This is a **single-query demo app** — no routing, no persistent history, no complex state management library. All state lives in `App.tsx` using React's built-in `useState` and `useEffect`.

**Do NOT use**: Redux, Zustand, Jotai, React Query, Context API.
**DO use**: `useState` + prop drilling (component tree is shallow).

---

## State Shape

All query state is owned by `App.tsx` and passed down as props:

```typescript
interface QueryState {
  // Input
  question: string;

  // Status
  isLoading: boolean;
  error: string | null;

  // Response
  answer: string;
  seedNodes: SeedNode[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  cypher: string;
  latencyMs: number | null;
}

const INITIAL_STATE: QueryState = {
  question: "",
  isLoading: false,
  error: null,
  answer: "",
  seedNodes: [],
  nodes: [],
  edges: [],
  cypher: "",
  latencyMs: null,
};
```

---

## `App.tsx`

```typescript
/**
 * App.tsx — Root layout and state owner
 *
 * Owns all query state.
 * Renders three-panel layout: ChatPanel | GraphViewer | CypherPanel
 */

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { ChatPanel } from "@/components/ChatPanel";
import { GraphViewer } from "@/components/GraphViewer";
import { CypherPanel } from "@/components/CypherPanel";
import { queryGraph } from "@/lib/api";
import type { SeedNode, GraphNode, GraphEdge } from "@/types/api";

const EXAMPLE_QUESTIONS = [
  "What methods are used for object detection?",
  "Which papers introduced transformer architectures?",
  "What datasets are used to benchmark image classification?",
  "How does BERT relate to other NLP methods?",
];

export function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [seedNodes, setSeedNodes] = useState<SeedNode[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [cypher, setCypher] = useState("");
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const handleSubmit = async (question: string) => {
    setIsLoading(true);
    setError(null);
    // Clear previous results
    setAnswer("");
    setSeedNodes([]);
    setNodes([]);
    setEdges([]);
    setCypher("");
    setLatencyMs(null);

    try {
      const response = await queryGraph(question);
      setAnswer(response.answer);
      setSeedNodes(response.seed_nodes);
      setNodes(response.nodes);
      setEdges(response.edges);
      setCypher(response.cypher_used);
      setLatencyMs(response.latency_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const seedNodeIds = new Set(seedNodes.map((sn) => sn.id));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">graphrag-neo4j</h1>
        <p className="text-sm text-slate-400">Graph RAG over ML Research Papers</p>
      </header>

      {error && (
        <div className="mb-4 p-3 rounded bg-red-900/50 border border-red-700 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 h-[calc(100vh-120px)]">
        {/* Left: Chat */}
        <Card className="p-4 flex flex-col bg-slate-900 border-slate-800">
          <ChatPanel
            onSubmit={handleSubmit}
            answer={answer}
            seedNodes={seedNodes}
            isLoading={isLoading}
            latencyMs={latencyMs ?? undefined}
            exampleQuestions={EXAMPLE_QUESTIONS}
          />
        </Card>

        {/* Right: Graph + Cypher */}
        <div className="flex flex-col gap-3">
          <Card className="flex-1 bg-slate-900 border-slate-800 overflow-hidden">
            <GraphViewer nodes={nodes} edges={edges} seedNodeIds={seedNodeIds} />
          </Card>
          {cypher && (
            <Card className="p-3 bg-slate-900 border-slate-800">
              <CypherPanel cypher={cypher} />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## State Update Rules

### Always clear stale state before a new query

```typescript
// ✅ Clear previous results BEFORE the async call
setAnswer("");
setSeedNodes([]);
setNodes([]);
// ... then make the API call

// ❌ Don't clear AFTER — causes flash of stale data if fast response
const response = await queryGraph(question);
setAnswer("");  // ❌ wrong order
```

### Always reset loading state in `finally`

```typescript
try {
  setIsLoading(true);
  const response = await queryGraph(question);
  // ... set state
} catch (err) {
  setError(...)
} finally {
  setIsLoading(false);  // ✅ Always runs — prevents stuck loading state
}
```

### Never mutate state arrays — always create new arrays

```typescript
// ✅ Immutable update
setNodes((prev) => [...prev, newNode]);

// ❌ Never mutate
setNodes((prev) => {
  prev.push(newNode);  // ❌ mutates!
  return prev;
});
```

---

## Derived State

Prefer deriving values instead of storing them separately:

```typescript
// ✅ Derive seedNodeIds from seedNodes
const seedNodeIds = new Set(seedNodes.map((sn) => sn.id));
// Passed to GraphViewer — recomputed on every render (cheap)

// ❌ Don't store derived state separately
const [seedNodeIds, setSeedNodeIds] = useState(new Set<string>());
// Now you need to keep it in sync manually
```

---

## Loading State Patterns

```typescript
// ChatPanel: disable input + show "Thinking..." text
<Button disabled={isLoading}>
  {isLoading ? "Thinking..." : "Ask"}
</Button>

// GraphViewer: show empty/previous graph (don't unmount — canvas is expensive to re-mount)
<GraphViewer nodes={nodes} edges={edges} seedNodeIds={seedNodeIds} />
// nodes/edges will be [] during loading → graph shows empty, which is fine

// Error state: show banner above layout
{error && <div className="error-banner">{error}</div>}
```

---

## Component → State Flow

```
User types question
    ↓
<Input> onChange → setQuestion (local to ChatPanel)
    ↓
User presses Enter or clicks Ask
    ↓
ChatPanel.onSubmit(question) → App.handleSubmit(question)
    ↓
setIsLoading(true) + clear stale state
    ↓
await queryGraph(question)    ← lib/api.ts
    ↓
Success:
  setAnswer(response.answer)
  setSeedNodes(response.seed_nodes)
  setNodes(response.nodes)
  setEdges(response.edges)
  setCypher(response.cypher_used)
  setLatencyMs(response.latency_ms)
    ↓
Error:
  setError("Something went wrong...")
    ↓
finally: setIsLoading(false)
    ↓
Re-render → props flow down to ChatPanel, GraphViewer, CypherPanel
```

---

## TypeScript State Types

All state types come from `@/types/api.ts` — never define inline types for state:

```typescript
// ✅ Import from types/api.ts
import type { SeedNode, GraphNode, GraphEdge } from "@/types/api";
const [seedNodes, setSeedNodes] = useState<SeedNode[]>([]);

// ❌ Don't define inline
const [seedNodes, setSeedNodes] = useState<{ id: string; label: string }[]>([]);
```

See [[projects/graphrag-neo4j/specs/frontend/api-client]] for type definitions.

---

## Future State (v2 / Out of Scope for MVP)

These patterns are intentionally deferred — do NOT implement in v1:

| Feature | Why Deferred |
|---------|-------------|
| Chat history (`messages: Message[]`) | Adds complexity, single-query demo is cleaner |
| React Query / SWR | Overkill for a single endpoint |
| Global context / store | Component tree is shallow — prop drilling is fine |
| URL state (`?q=...`) | Not needed for portfolio demo |
