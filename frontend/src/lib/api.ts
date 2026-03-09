/**
 * lib/api.ts
 *
 * API client for graphrag-neo4j backend.
 * All fetch calls go through this module.
 */

import type {
  ExploreResponse,
  GraphStats,
  HealthResponse,
  Neo4jPingResponse,
  PingResponse,
  QueryResponse,
  SchemaResponse,
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
