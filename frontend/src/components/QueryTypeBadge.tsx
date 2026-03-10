import { Badge } from "@/components/ui/badge";

const QUERY_TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  FACTUAL_LOOKUP: {
    label: "Factual",
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  COMPARISON: {
    label: "Comparison",
    className: "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20",
  },
  TEMPORAL: {
    label: "Temporal",
    className: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  NETWORK: {
    label: "Network",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  EXPLORATORY: {
    label: "Exploratory",
    className: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20",
  },
  AGGREGATION: {
    label: "Aggregation",
    className: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  },
  MULTI_HOP: {
    label: "Multi-Hop",
    className: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20",
  },
};

interface QueryTypeBadgeProps {
  queryType: string;
}

export function QueryTypeBadge({ queryType }: QueryTypeBadgeProps) {
  if (!queryType) return null;

  const config = QUERY_TYPE_CONFIG[queryType] ?? {
    label: queryType.replace(/_/g, " "),
    className: "bg-muted text-muted-foreground border-border",
  };

  return (
    <Badge variant="outline" className={`text-[10px] font-medium py-0 ${config.className}`}>
      {config.label}
    </Badge>
  );
}
