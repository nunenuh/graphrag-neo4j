import { Badge } from "@/components/ui/badge";
import { ArrowRight, CircleDot, GitBranch } from "lucide-react";
import type { TraversalStep } from "@/types/api";

const HOP_COLORS = [
  "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
];

interface TraversalPathProps {
  steps: TraversalStep[];
}

export function TraversalPath({ steps }: TraversalPathProps) {
  if (steps.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
        <GitBranch size={11} />
        <span>Traversal path</span>
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {steps.map((step, i) => (
          <div key={step.hop} className="flex items-center gap-1">
            {i > 0 && (
              <ArrowRight size={10} className="text-muted-foreground/50 shrink-0" />
            )}
            <div className="flex items-center gap-1.5 rounded-md border border-border/50 bg-secondary/40 px-2 py-1">
              <CircleDot size={10} className={i === 0 ? "text-blue-500" : i === 1 ? "text-emerald-500" : "text-purple-500"} />
              <span className="text-[11px] text-foreground/80">{step.description}</span>
              <div className="flex gap-0.5">
                {step.node_labels.map((label) => (
                  <Badge
                    key={label}
                    variant="outline"
                    className={`text-[9px] px-1 py-0 font-normal ${HOP_COLORS[i] ?? HOP_COLORS[0]}`}
                  >
                    {label}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
