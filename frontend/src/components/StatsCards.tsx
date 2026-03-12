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
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STAT_ITEMS.map(({ key, label, icon: Icon, color }) => (
          <Card key={key} className="bg-card/50 border-border/50 backdrop-blur-sm shadow-sm hover:bg-card/80 transition-all duration-300 group overflow-hidden relative">
            <div className={`absolute top-0 right-0 w-24 h-24 ${COLOR_MAP[color].replace('border-', '')} opacity-10 rounded-bl-full blur-2xl transform translate-x-1/2 -translate-y-1/2 transition-transform group-hover:scale-150`}></div>
            <CardContent className="p-5 relative z-10">
              <div className="flex items-center gap-4">
                <div
                  className={`flex items-center justify-center w-12 h-12 rounded-xl border ${COLOR_MAP[color]}`}
                >
                  <Icon size={20} />
                </div>
                <div>
                  <p className="text-3xl font-bold tracking-tight text-foreground tabular-nums">
                    {stats ? (stats.node_counts[key] ?? 0).toLocaleString() : "---"}
                  </p>
                  <p className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">{label}</p>
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
