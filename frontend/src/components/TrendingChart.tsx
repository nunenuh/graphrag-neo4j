import type { TrendingItem } from "@/types/api";
import { TrendingUp } from "lucide-react";

interface TrendingChartProps {
  title: string;
  items: TrendingItem[];
  color: string;
}

export function TrendingChart({ title, items, color }: TrendingChartProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <TrendingUp size={24} className="mb-2 opacity-40" />
        <p className="text-xs">No {title.toLowerCase()} data yet.</p>
      </div>
    );
  }

  const maxScore = Math.max(...items.map((i) => i.trend_score));

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {title}
      </h3>
      <div className="space-y-1.5">
        {items.map((item) => {
          const pct = maxScore > 0 ? (item.trend_score / maxScore) * 100 : 0;
          return (
            <div key={item.uid} className="flex items-center gap-2">
              <span className="text-xs text-foreground/80 w-36 truncate shrink-0" title={item.name}>
                {item.name}
              </span>
              <div className="flex-1 h-5 rounded bg-secondary/50 overflow-hidden">
                <div
                  className="h-full rounded transition-all duration-300"
                  style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
                />
              </div>
              <span className="text-[11px] text-muted-foreground tabular-nums w-12 text-right shrink-0">
                {item.trend_score.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
