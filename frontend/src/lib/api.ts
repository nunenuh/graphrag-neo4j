/**
 * lib/api.ts
 *
 * API client for graphrag-neo4j backend.
 * All fetch calls go through this module.
 */

import type {
  AnalyticsRunResponse,
  CommunitiesResponse,
  EvalQueriesResponse,
  EvalReport,
  ExploreResponse,
  GraphStats,
  HealthResponse,
  Neo4jPingResponse,
  NodeDetail,
  PingResponse,
  QueryResponse,
  SchemaResponse,
  SearchResponse,
  TrendsResponse,
} from "@/types/api";
import { ApiError } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

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
      detail = response.statusText || detail;
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

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

export async function fetchGraphStats(): Promise<GraphStats> {
  return apiFetch<GraphStats>("/api/v1/graph/stats");
}

export async function searchNodes(
  q: string,
  label?: string,
  limit = 20,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (label) params.set("label", label);
  return apiFetch<SearchResponse>(`/api/v1/graph/search?${params}`);
}

export async function fetchNodeDetail(uid: string): Promise<NodeDetail> {
  return apiFetch<NodeDetail>(`/api/v1/graph/nodes/${encodeURIComponent(uid)}`);
}

export async function runAnalytics(): Promise<AnalyticsRunResponse> {
  return apiFetch<AnalyticsRunResponse>("/api/v1/analytics/run", {
    method: "POST",
  });
}

export async function fetchCommunities(
  limit = 50,
): Promise<CommunitiesResponse> {
  return apiFetch<CommunitiesResponse>(
    `/api/v1/analytics/communities?limit=${limit}`,
  );
}

export async function fetchTrends(
  type: "Method" | "Task" = "Method",
  limit = 10,
): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>(
    `/api/v1/analytics/trends?type=${type}&limit=${limit}`,
  );
}

export async function fetchEvalQueries(
  category?: string,
): Promise<EvalQueriesResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch<EvalQueriesResponse>(`/api/v1/eval/queries${params}`);
}

export async function runEvaluation(
  category?: string,
): Promise<EvalReport> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch<EvalReport>(`/api/v1/eval/run${params}`, {
    method: "POST",
  });
}

export async function fetchLatestReport(): Promise<EvalReport> {
  return apiFetch<EvalReport>("/api/v1/eval/report/latest");
}
