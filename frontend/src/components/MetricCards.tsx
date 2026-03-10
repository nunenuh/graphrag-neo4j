interface MetricCardsProps {
  metrics: Record<string, number>;
}

const METRIC_CONFIG: Record<string, { label: string; format: (v: number) => string; color: string }> = {
  entity_f1: { label: "Entity F1", format: (v) => v.toFixed(3), color: "text-blue-500" },
  precision_at_10: { label: "Precision@10", format: (v) => v.toFixed(3), color: "text-emerald-500" },
  recall_at_10: { label: "Recall@10", format: (v) => v.toFixed(3), color: "text-violet-500" },
  keyword_coverage: { label: "Keyword Coverage", format: (v) => v.toFixed(3), color: "text-amber-500" },
  provenance_score: { label: "Provenance", format: (v) => v.toFixed(3), color: "text-cyan-500" },
  latency_p95: { label: "Latency P95", format: (v) => `${v.toFixed(0)}ms`, color: "text-rose-500" },
};

const DISPLAY_ORDER = ["entity_f1", "precision_at_10", "recall_at_10", "keyword_coverage", "provenance_score", "latency_p95"];

export function MetricCards({ metrics }: MetricCardsProps) {
  const keys = DISPLAY_ORDER.filter((k) => k in metrics);

  if (keys.length === 0) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
      {keys.map((key) => {
        const config = METRIC_CONFIG[key] ?? { label: key, format: (v: number) => v.toFixed(3), color: "text-foreground" };
        return (
          <div
            key={key}
            className="rounded-lg border border-border/50 bg-card p-3 text-center"
          >
            <div className={`text-xl font-bold tabular-nums ${config.color}`}>
              {config.format(metrics[key])}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">
              {config.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
