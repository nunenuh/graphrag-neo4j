/**
 * types/api.ts
 *
 * TypeScript types mirroring the graphrag-neo4j API spec.
 * Source of truth: docs/technical/api-spec.md
 */

// Shared types

export type NodeLabel = "Paper" | "Method" | "Task" | "Dataset" | "Author" | "Repository";

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

export type QueryType =
  | "FACTUAL_LOOKUP"
  | "COMPARISON"
  | "TEMPORAL"
  | "NETWORK"
  | "EXPLORATORY"
  | "AGGREGATION"
  | "MULTI_HOP";

export type RetrievalStrategy =
  | "GRAPH_ONLY"
  | "VECTOR_ONLY"
  | "HYBRID_PARALLEL"
  | "HYBRID_SEQUENTIAL";

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
  step_timings: Record<string, number | Record<string, number>>;
  query_type: string;
  retrieval_strategy: string;
  provenance_score: number | null;
  unsupported_claims: string[];
}

// Traversal path (hop-by-hop explanation)

export interface TraversalStep {
  hop: number;
  node_count: number;
  node_labels: string[];
  label_counts: Record<string, number>;
  edge_types: string[];
  description: string;
}

// Main response

export interface QueryResponse {
  answer: string;
  seed_nodes: SeedNode[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  cypher_used: string;
  traversal_path: TraversalStep[];
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

// /api/v1/analytics/run

export interface AnalyticsRunResponse {
  communities_detected: number;
  authors_with_centrality: number;
  methods_with_trends: number;
  tasks_with_trends: number;
  message: string;
}

// /api/v1/analytics/communities

export interface CommunityMember {
  uid: string;
  name: string;
  pagerank?: number;
}

export interface Community {
  community_id: number;
  member_count: number;
  top_members: CommunityMember[];
}

export interface CommunitiesResponse {
  total_communities: number;
  communities: Community[];
}

// /api/v1/analytics/trends

export interface TrendingItem {
  uid: string;
  name: string;
  trend_score: number;
}

export interface TrendsResponse {
  entity_type: string;
  items: TrendingItem[];
}

// /api/v1/eval/queries

export interface EvalQueryInfo {
  id: string;
  category: string;
  question: string;
  difficulty: string;
  expected_entities: string[];
  min_hops: number;
}

export interface EvalQueriesResponse {
  queries: EvalQueryInfo[];
  count: number;
}

// /api/v1/eval/run & /api/v1/eval/report/latest

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

export interface EvalReport {
  timestamp: string;
  system_name: string;
  total_queries: number;
  successful_queries: number;
  metrics_summary: Record<string, number>;
  metrics_by_category: Record<string, Record<string, number>>;
  failures: string[];
  comparison: Record<string, Record<string, number>> | null;
  results: EvalResultItem[];
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
