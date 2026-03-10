import { Progress } from "@/components/ui/progress";
import { ShieldCheck } from "lucide-react";

interface ProvenanceBadgeProps {
  score: number | null;
}

function getColor(score: number): string {
  if (score >= 0.8) return "text-emerald-500";
  if (score >= 0.5) return "text-amber-500";
  return "text-red-500";
}

function getBarClass(score: number): string {
  if (score >= 0.8) return "[&>div]:bg-emerald-500";
  if (score >= 0.5) return "[&>div]:bg-amber-500";
  return "[&>div]:bg-red-500";
}

export function ProvenanceBadge({ score }: ProvenanceBadgeProps) {
  if (score === null || score === undefined) return null;

  const pct = Math.round(score * 100);

  return (
    <div className="flex items-center gap-2">
      <ShieldCheck size={12} className={`shrink-0 ${getColor(score)}`} />
      <span className="text-[11px] text-muted-foreground shrink-0">Provenance</span>
      <Progress value={pct} className={`h-1.5 flex-1 ${getBarClass(score)}`} />
      <span className={`text-[11px] font-medium tabular-nums ${getColor(score)}`}>
        {pct}%
      </span>
    </div>
  );
}
