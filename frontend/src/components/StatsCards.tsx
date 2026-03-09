import { FileText, Cpu, Target, Database } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { GraphStats } from "@/types/api";

const STAT_ITEMS = [
  { key: "Paper", label: "Papers", icon: FileText, color: "blue" },
  { key: "Method", label: "Methods", icon: Cpu, color: "emerald" },
  { key: "Task", label: "Tasks", icon: Target, color: "purple" },
  { key: "Dataset", label: "Datasets", icon: Database, color: "orange" },
] as const;

const COLOR_MAP: Record<string, string> = {
  blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  purple: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  orange: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
};

interface StatsCardsProps {
  stats: GraphStats | null;
}

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-3">
        {STAT_ITEMS.map(({ key, label, icon: Icon, color }) => (
          <Card key={key} className="border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div
                  className={`flex items-center justify-center w-9 h-9 rounded-lg border ${COLOR_MAP[color]}`}
                >
                  <Icon size={16} />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-foreground tabular-nums">
                    {stats ? (stats.node_counts[key] ?? 0).toLocaleString() : "---"}
                  </p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {stats && (
        <p className="text-xs text-muted-foreground text-center">
          {stats.total_nodes.toLocaleString()} total nodes
          {" · "}
          {stats.total_edges.toLocaleString()} total relationships
        </p>
      )}
    </div>
  );
}
