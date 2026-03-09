import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <BarChart3 size={48} className="mx-auto text-muted-foreground/40" />
        <h2 className="text-lg font-semibold text-foreground">Graph Analytics</h2>
        <p className="text-sm text-muted-foreground">
          Communities, trends, and centrality rankings. Coming in Phase D.
        </p>
      </div>
    </div>
  );
}
