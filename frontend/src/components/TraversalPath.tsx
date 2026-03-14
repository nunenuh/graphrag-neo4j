import { Search, ArrowDown, Network } from "lucide-react";
import type { TraversalStep } from "@/types/api";

const LABEL_COLORS: Record<string, string> = {
  Paper: "text-blue-600 dark:text-blue-400",
  Method: "text-emerald-600 dark:text-emerald-400",
  Task: "text-purple-600 dark:text-purple-400",
  Dataset: "text-orange-600 dark:text-orange-400",
  Author: "text-slate-600 dark:text-slate-400",
};

const HOP_ICONS = [Search, Network, Network];

interface TraversalPathProps {
  steps: TraversalStep[];
}

export function TraversalPath({ steps }: TraversalPathProps) {
  if (steps.length === 0) return null;

  const totalNodes = steps.reduce((sum, s) => sum + s.node_count, 0);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
          How this answer was built
        </span>
        <span className="text-[10px] text-muted-foreground/60 tabular-nums">
          {totalNodes} nodes explored
        </span>
      </div>
      <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-2 space-y-0">
        {steps.map((step, i) => {
          const Icon = HOP_ICONS[i] ?? Network;
          return (
            <div key={step.hop}>
              {i > 0 && (
                <div className="flex items-center gap-2 py-0.5">
                  <div className="w-4 flex justify-center">
                    <ArrowDown size={8} className="text-muted-foreground/40" />
                  </div>
                </div>
              )}
              <div className="flex items-start gap-2">
                <div className="w-4 flex justify-center pt-0.5">
                  <Icon size={11} className={i === 0 ? "text-blue-500" : "text-emerald-500"} />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] text-foreground/80">{step.description}</span>
                  {Object.keys(step.label_counts).length > 0 && (
                    <div className="flex gap-2 mt-0.5">
                      {Object.entries(step.label_counts)
                        .sort(([, a], [, b]) => b - a)
                        .map(([label, count]) => (
                          <span
                            key={label}
                            className={`text-[10px] tabular-nums ${LABEL_COLORS[label] ?? "text-muted-foreground"}`}
                          >
                            {count} {label}{count > 1 ? "s" : ""}
                          </span>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
