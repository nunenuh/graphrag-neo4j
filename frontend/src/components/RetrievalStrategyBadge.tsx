import { Database, Search, GitMerge, ArrowRight } from "lucide-react";

const STRATEGY_CONFIG: Record<string, { label: string; Icon: typeof Database }> = {
  GRAPH_ONLY: { label: "Graph Only", Icon: Database },
  VECTOR_ONLY: { label: "Vector Only", Icon: Search },
  HYBRID_PARALLEL: { label: "Hybrid Parallel", Icon: GitMerge },
  HYBRID_SEQUENTIAL: { label: "Hybrid Sequential", Icon: ArrowRight },
};

interface RetrievalStrategyBadgeProps {
  strategy: string;
}

export function RetrievalStrategyBadge({ strategy }: RetrievalStrategyBadgeProps) {
  if (!strategy) return null;

  const config = STRATEGY_CONFIG[strategy] ?? {
    label: strategy.replace(/_/g, " "),
    Icon: Search,
  };
  const { label, Icon } = config;

  return (
    <div className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <Icon size={11} className="shrink-0" />
      <span>{label}</span>
    </div>
  );
}
