# Frontend Spec: API Client

File: `frontend/src/lib/api.ts` · `frontend/src/types/api.ts`

See also: [[projects/graphrag-neo4j/docs/technical/api-spec]] · [[projects/graphrag-neo4j/specs/backend/api]]

---

## Structure

```
frontend/src/
├── lib/
│   └── api.ts        ← API call functions (fetch wrappers)
└── types/
    └── api.ts        ← TypeScript interfaces mirroring API spec
```

**Rule**: Types and API functions are in separate files.
- `types/api.ts` — pure TypeScript interfaces, no logic
- `lib/api.ts` — fetch calls, error handling, URL construction

---

## `src/types/api.ts`

TypeScript types that mirror the backend API spec **exactly**. When the API spec changes, update here first.

```typescript
/**
 * types/api.ts
 *
 * TypeScript types mirroring the graphrag-neo4j API spec.
 * Source of truth: docs/technical/api-spec.md
 */

// Shared types
export type NodeLabel = "Paper" | "Method" | "Task" | "Dataset";

// Request
export interface QueryRequest {
  question: string;
}

// Response sub-types
export interface SeedNode {
  id: string;
  label: NodeLabel;
  name: string;
  score: number;
}

export interface GraphNode {
  id: string;
  uid?: string;          // Backend returns uid as primary ID
  label: NodeLabel;
  name: string;
  title?: string;
  description?: string;
  [key: string]: unknown; // Extra properties per node type
}

export interface GraphEdge {
  from_id: string;
  to_id: string;
  type: string;
  properties: Record<string, string>;
}

// Pipeline metadata for evaluation
export interface PipelineMetadata {
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  top_k: number;
  traversal_depth: number;
  seed_count: number;
  node_count: number;
  edge_count: number;
  context_length: number;
  step_timings: Record<string, number>; // step name → ms
}

// Main response
export interface QueryResponse {
  answer: string;
  seed_nodes: SeedNode[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  cypher_used: string;
  latency_ms: number;
  metadata: PipelineMetadata | null;
}

// /api/v1/graph/schema
export interface SchemaResponse {
  node_labels: NodeLabel[];
  relationship_types: string[];
}

// /api/v1/graph/explore
export interface ExploreNode { id: string; name: string; label: NodeLabel; }
export interface ExploreEdge { from_id: string; to_id: string; type: string; }
export interface ExploreResponse { nodes: ExploreNode[]; edges: ExploreEdge[]; }

// /api/v1/health/ping
export interface PingResponse {
  status: string;
  timestamp: string;
  message: string;
}

// /api/v1/health/neo4j
export interface Neo4jPingResponse {
  status: "healthy" | "unhealthy";
  message: string;
  response_time_ms: number;
  timestamp: string;
}

// /api/v1/health/status
export interface ComponentHealth {
  name: string;
  status: "healthy" | "unhealthy";
  message: string | null;
  response_time_ms: number | null;
}

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  version: string;
  components: ComponentHealth[];
  uptime_seconds: number;
}

// Client-side error type
export class ApiError extends Error {
  statusCode: number;
  detail: string;
  constructor(statusCode: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.detail = detail;
  }
}
```

---

## `src/lib/api.ts`

```typescript
/**
 * lib/api.ts
 *
 * API client for graphrag-neo4j backend.
 * All fetch calls go through this module.
 *
 * Base URL: import.meta.env.VITE_API_URL (set in frontend/.env)
 */

import type {
  ExploreResponse,
  HealthResponse,
  Neo4jPingResponse,
  PingResponse,
  QueryResponse,
  SchemaResponse,
} from "@/types/api";
import { ApiError } from "@/types/api";

// ─────────────────────────────────────────────
// Base URL
// ─────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? "";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

// ─────────────────────────────────────────────
// Core fetch helper
// ─────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Response body is not JSON — use status text
      detail = response.statusText || detail;
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

// ─────────────────────────────────────────────
// API functions
// ─────────────────────────────────────────────

/**
 * POST /api/query
 *
 * Run the Graph RAG pipeline for a natural language question.
 *
 * @param question - Natural language question about ML research
 * @throws ApiError if the request fails
 */
export async function queryGraph(question: string): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/api/v1/rag/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function fetchSchema(): Promise<SchemaResponse> {
  return apiFetch<SchemaResponse>("/api/v1/graph/schema");
}

export async function exploreGraph(limit = 50): Promise<ExploreResponse> {
  return apiFetch<ExploreResponse>(`/api/v1/graph/explore?limit=${limit}`);
}

export async function pingBackend(): Promise<PingResponse> {
  return apiFetch<PingResponse>("/api/v1/health/ping");
}

export async function pingNeo4j(): Promise<Neo4jPingResponse> {
  return apiFetch<Neo4jPingResponse>("/api/v1/health/neo4j");
}

export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health/status");
}
```

---

## Error Handling in Components

Use `ApiError` to distinguish API errors from network errors:

```typescript
// In App.tsx handleSubmit
try {
  const response = await queryGraph(question);
  // ...
} catch (err) {
  if (err instanceof ApiError) {
    // Known API error — show specific message
    setError(`API error (${err.statusCode}): ${err.detail}`);
  } else {
    // Network error (no connection, CORS, etc.)
    setError("Network error. Is the backend running?");
  }
}
```

| Error Type | When | User Message |
|-----------|------|-------------|
| `ApiError(400, ...)` | Empty question (shouldn't reach API, but just in case) | `"Please enter a question"` |
| `ApiError(500, ...)` | Backend crash / Neo4j down | `"Server error. Please try again."` |
| `TypeError: Failed to fetch` | Backend not running / CORS | `"Network error. Is the backend running?"` |
| `ApiError(422, ...)` | Pydantic validation fail | Show `err.detail` |

---

## Vite Environment Variables

```bash
# frontend/.env  (development)
VITE_API_URL=http://localhost:8005
VITE_API_KEY=changeme-in-production   # Same value as APP_X_API_KEY

# frontend/.env.production
VITE_API_URL=https://your-api-domain.com
VITE_API_KEY=your-production-api-key
```

**Rules:**
- All Vite env vars **must** be prefixed with `VITE_`
- Access with `import.meta.env.VITE_API_URL` — NOT `process.env.*`
- `VITE_API_URL` defaults to `""` (empty) when using Vite dev proxy
- `VITE_API_KEY` is sent as `X-API-Key` header on all requests (matching backend `APP_X_API_KEY`)
- Never commit `.env` files with secrets — `.env.example` only

---

## `vite.config.ts` — Dev Proxy (Optional)

If you want to avoid CORS in development, configure a proxy in Vite:

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

With this proxy, `VITE_API_URL` can be empty and requests to `/api/*` forward to FastAPI.

---

## TypeScript Import Rules

```typescript
// ✅ Use type imports for types only
import type { QueryResponse, SeedNode } from "@/types/api";

// ✅ Use value import for class (needed at runtime)
import { ApiError } from "@/types/api";

// ✅ Use path alias @/ for src-relative imports
import { queryGraph } from "@/lib/api";

// ❌ Don't use relative paths from deeply nested files
import { queryGraph } from "../../../lib/api";
```

The `@/` alias is configured in `vite.config.ts` and `tsconfig.json`.

---

## `tsconfig.json` Path Aliases

```json
{
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```
