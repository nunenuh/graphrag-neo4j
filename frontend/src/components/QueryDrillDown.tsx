import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { EvalResultItem } from "@/types/api";

interface QueryDrillDownProps {
  results: EvalResultItem[];
  categoryFilter: string | null;
}

export function QueryDrillDown({ results, categoryFilter }: QueryDrillDownProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = categoryFilter
    ? results.filter((r) => r.category === categoryFilter)
    : results;

  // Group by category
  const grouped: Record<string, EvalResultItem[]> = {};
  for (const r of filtered) {
    if (!grouped[r.category]) grouped[r.category] = [];
    grouped[r.category].push(r);
  }

  if (filtered.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No query results available.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(grouped)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([category, items]) => (
          <div key={category}>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
              {category.replace(/_/g, " ")} ({items.length})
            </h3>
            <div className="space-y-1">
              {items.map((r) => {
                const isExpanded = expandedId === r.query_id;
                return (
                  <div
                    key={r.query_id}
                    className="rounded-lg border border-border/50 bg-card overflow-hidden"
                  >
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : r.query_id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-secondary/50 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown size={14} className="text-muted-foreground shrink-0" />
                      ) : (
                        <ChevronRight size={14} className="text-muted-foreground shrink-0" />
                      )}
                      <span className="text-xs text-muted-foreground tabular-nums shrink-0 w-20">
                        {r.query_id}
                      </span>
                      <span className="text-xs text-foreground/80 truncate flex-1">
                        {r.question}
                      </span>
                      {r.metrics.entity_f1 !== undefined && (
                        <span className="text-[10px] tabular-nums text-muted-foreground shrink-0">
                          F1: {r.metrics.entity_f1.toFixed(2)}
                        </span>
                      )}
                    </button>
                    {isExpanded && (
                      <div className="px-3 pb-3 pt-0 border-t border-border/30">
                        <div className="pt-2 space-y-2">
                          {/* Answer */}
                          <div>
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Answer</span>
                            <p className="text-xs text-foreground/80 mt-0.5 whitespace-pre-wrap">
                              {r.answer || "No answer"}
                            </p>
                          </div>
                          {/* Metrics */}
                          <div>
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Metrics</span>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                              {Object.entries(r.metrics)
                                .filter(([k]) => k !== "error")
                                .map(([k, v]) => (
                                  <span key={k} className="text-[11px]">
                                    <span className="text-muted-foreground">{k.replace(/_/g, " ")}:</span>{" "}
                                    <span className="font-medium tabular-nums">
                                      {k.includes("latency") ? `${v.toFixed(0)}ms` : v.toFixed(3)}
                                    </span>
                                  </span>
                                ))}
                            </div>
                          </div>
                          {/* Meta */}
                          <div className="flex gap-4 text-[10px] text-muted-foreground">
                            {r.query_type && <span>Type: {r.query_type}</span>}
                            {r.retrieval_strategy && <span>Strategy: {r.retrieval_strategy}</span>}
                            <span>Latency: {r.latency_ms}ms</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
    </div>
  );
}
