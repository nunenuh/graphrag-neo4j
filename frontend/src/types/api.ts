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
  uid?: string;
  label: NodeLabel;
  name: string;
  title?: string;
  description?: string;
  [key: string]: unknown;
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
  step_timings: Record<string, number>;
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

export interface ExploreNode {
  id?: string;
  uid?: string;
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

// /api/v1/graph/stats

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
}

// /api/v1/graph/search

export interface SearchResult {
  uid: string;
  label: string;
  name: string;
  properties: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  count: number;
}

// /api/v1/graph/nodes/{uid}

export interface NodeDetail {
  uid: string;
  label: string;
  properties: Record<string, unknown>;
  outgoing: Array<{ to: string; type: string }>;
  incoming: Array<{ from: string; type: string }>;
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
