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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {keys.map((key) => {
        const config = METRIC_CONFIG[key] ?? { label: key, format: (v: number) => v.toFixed(3), color: "text-foreground" };
        return (
          <div
            key={key}
            className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm shadow-sm hover:bg-card/80 transition-all duration-300 p-4 text-center group relative overflow-hidden"
          >
            <div className={`absolute -inset-1 opacity-0 group-hover:opacity-10 transition-opacity blur-xl ${config.color.replace('text-', 'bg-')}`}></div>
            <div className={`relative z-10 text-2xl font-bold tabular-nums tracking-tight ${config.color}`}>
              {config.format(metrics[key])}
            </div>
            <div className="relative z-10 text-xs font-medium text-muted-foreground mt-2 uppercase tracking-wider group-hover:text-foreground transition-colors">
              {config.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
