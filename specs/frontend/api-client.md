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

// ─────────────────────────────────────────────
// Shared types
// ─────────────────────────────────────────────

export type NodeLabel = "Paper" | "Method" | "Task" | "Dataset";

// ─────────────────────────────────────────────
// Request
// ─────────────────────────────────────────────

export interface QueryRequest {
  question: string;
}

// ─────────────────────────────────────────────
// Response sub-types
// ─────────────────────────────────────────────

export interface SeedNode {
  id: string;
  label: NodeLabel;
  name: string;
  score: number;  // 0.0 – 1.0, cosine similarity
}

export interface GraphNode {
  id: string;
  label: NodeLabel;
  name: string;    // For Method / Task / Dataset
  title: string;   // For Paper
  description: string;
}

export interface GraphEdge {
  from_id: string;
  to_id: string;
  type: string;    // "INTRODUCES" | "APPLIED_ON" | "EVALUATED_ON" | ...
  properties: Record<string, string>;  // e.g. { metric: "mAP", score: "45.5" }
}

// ─────────────────────────────────────────────
// Main response
// ─────────────────────────────────────────────

export interface QueryResponse {
  answer: string;
  seed_nodes: SeedNode[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  cypher_used: string;
  latency_ms: number;
}

// ─────────────────────────────────────────────
// /api/graph/schema
// ─────────────────────────────────────────────

export interface SchemaResponse {
  node_labels: NodeLabel[];
  relationship_types: string[];
}

// ─────────────────────────────────────────────
// /api/graph/explore
// ─────────────────────────────────────────────

export interface ExploreNode {
  id: string;
  name: string;
  label: NodeLabel;
}

export interface ExploreEdge {
  from_id: string;
  to_id: string;
  type: string;
}

export interface ExploreResponse {
  nodes: ExploreNode[];
  edges: ExploreEdge[];
}

// ─────────────────────────────────────────────
// /api/health
// ─────────────────────────────────────────────

export type Neo4jStatus = "connected" | "error";

export interface HealthResponse {
  status: "ok";
  neo4j: Neo4jStatus;
  version: string;
}

// ─────────────────────────────────────────────
// Client-side error type
// ─────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
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
  QueryResponse,
  SchemaResponse,
} from "@/types/api";
import { ApiError } from "@/types/api";

// ─────────────────────────────────────────────
// Base URL
// ─────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
  return apiFetch<QueryResponse>("/api/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

/**
 * GET /api/graph/schema
 *
 * Fetch all node labels and relationship types.
 *
 * @throws ApiError if the request fails
 */
export async function fetchSchema(): Promise<SchemaResponse> {
  return apiFetch<SchemaResponse>("/api/graph/schema");
}

/**
 * GET /api/graph/explore
 *
 * Fetch a sample subgraph for initial visualization.
 *
 * @param limit - Max number of relationships to return (default 50, max 200)
 * @throws ApiError if the request fails
 */
export async function exploreGraph(limit = 50): Promise<ExploreResponse> {
  return apiFetch<ExploreResponse>(`/api/graph/explore?limit=${limit}`);
}

/**
 * GET /api/health
 *
 * Check API and Neo4j health.
 *
 * @throws ApiError if the request fails
 */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
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
VITE_API_URL=http://localhost:8000

# frontend/.env.production
VITE_API_URL=https://your-api-domain.com
```

**Rules:**
- All Vite env vars **must** be prefixed with `VITE_`
- Access with `import.meta.env.VITE_API_URL` — NOT `process.env.*`
- Provide a fallback in `api.ts`: `?? "http://localhost:8000"` for local dev without `.env`
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
