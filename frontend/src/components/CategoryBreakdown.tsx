import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface CategoryBreakdownProps {
  metricsByCategory: Record<string, Record<string, number>>;
}

const METRIC_COLS = ["entity_f1", "precision_at_10", "recall_at_10", "keyword_coverage", "provenance_score", "latency_ms"];
const COL_LABELS: Record<string, string> = {
  entity_f1: "F1",
  precision_at_10: "P@10",
  recall_at_10: "R@10",
  keyword_coverage: "Keywords",
  provenance_score: "Provenance",
  latency_ms: "Latency",
};

export function CategoryBreakdown({ metricsByCategory }: CategoryBreakdownProps) {
  const categories = Object.keys(metricsByCategory).sort();

  if (categories.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/50 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-secondary/30">
            <TableHead className="text-[11px]">Category</TableHead>
            {METRIC_COLS.map((col) => (
              <TableHead key={col} className="text-[11px] text-right">
                {COL_LABELS[col] ?? col}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {categories.map((cat) => {
            const metrics = metricsByCategory[cat];
            return (
              <TableRow key={cat}>
                <TableCell className="text-xs font-medium">
                  {cat.replace(/_/g, " ")}
                </TableCell>
                {METRIC_COLS.map((col) => {
                  const val = metrics[col];
                  return (
                    <TableCell key={col} className="text-xs text-right tabular-nums text-muted-foreground">
                      {val !== undefined
                        ? col === "latency_ms"
                          ? `${val.toFixed(0)}ms`
                          : val.toFixed(3)
                        : "—"}
                    </TableCell>
                  );
                })}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
