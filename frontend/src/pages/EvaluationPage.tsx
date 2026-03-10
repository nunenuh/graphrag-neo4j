import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricCards } from "@/components/MetricCards";
import { CategoryBreakdown } from "@/components/CategoryBreakdown";
import { QueryDrillDown } from "@/components/QueryDrillDown";
import { fetchLatestReport, runEvaluation } from "@/lib/api";
import type { EvalReport } from "@/types/api";
import { Loader2, Play, FlaskConical } from "lucide-react";

export default function EvaluationPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchLatestReport();
      setReport(data);
    } catch {
      // No cached report yet — that's fine
      setReport(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleRunEvaluation = async () => {
    try {
      setIsRunning(true);
      setError(null);
      const data = await runEvaluation(categoryFilter ?? undefined);
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setIsRunning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" size={32} />
      </div>
    );
  }

  const categories = report
    ? [...new Set(report.results.map((r) => r.category))].sort()
    : [];

  return (
    <div className="flex-1 flex flex-col gap-4 p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical size={20} className="text-muted-foreground" />
          <h1 className="text-lg font-semibold">Evaluation Dashboard</h1>
        </div>
        <div className="flex items-center gap-2">
          {categories.length > 0 && (
            <select
              value={categoryFilter ?? ""}
              onChange={(e) => setCategoryFilter(e.target.value || null)}
              className="text-xs border border-border rounded-md px-2 py-1.5 bg-background text-foreground"
            >
              <option value="">All categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          )}
          <button
            onClick={handleRunEvaluation}
            disabled={isRunning}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isRunning ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Play size={14} />
            )}
            {isRunning ? "Running…" : "Run Evaluation"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {!report ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <FlaskConical size={48} className="mx-auto text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              No evaluation report found. Click &quot;Run Evaluation&quot; to start.
            </p>
          </div>
        </div>
      ) : (
        <Tabs defaultValue="overview" className="flex-1 flex flex-col">
          <TabsList className="w-fit">
            <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
            <TabsTrigger value="baselines" className="text-xs">Baselines</TabsTrigger>
            <TabsTrigger value="queries" className="text-xs">Queries</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="flex-1 space-y-4 mt-3">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>System: {report.system_name}</span>
              <span>Queries: {report.successful_queries}/{report.total_queries}</span>
              <span>{report.timestamp}</span>
            </div>

            <MetricCards metrics={report.metrics_summary} />
            <CategoryBreakdown metricsByCategory={report.metrics_by_category} />

            {report.failures.length > 0 && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3">
                <h3 className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">
                  Failures ({report.failures.length})
                </h3>
                <ul className="text-[11px] text-red-600/80 dark:text-red-400/80 space-y-0.5">
                  {report.failures.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </TabsContent>

          {/* Baselines Tab */}
          <TabsContent value="baselines" className="flex-1 mt-3">
            {report.comparison ? (
              <BaselineTable comparison={report.comparison} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No baseline comparison available. Run evaluation with a baseline to compare.
              </p>
            )}
          </TabsContent>

          {/* Queries Tab */}
          <TabsContent value="queries" className="flex-1 mt-3">
            <QueryDrillDown results={report.results} categoryFilter={categoryFilter} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

/* ---------- Inline BaselineTable ---------- */

interface BaselineTableProps {
  comparison: Record<string, Record<string, number>>;
}

function BaselineTable({ comparison }: BaselineTableProps) {
  const systems = Object.keys(comparison);
  if (systems.length === 0) return null;

  const metricKeys = [...new Set(systems.flatMap((s) => Object.keys(comparison[s])))].sort();

  return (
    <div className="rounded-lg border border-border/50 overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-secondary/30">
            <th className="text-left px-3 py-2 text-muted-foreground font-medium">Metric</th>
            {systems.map((s) => (
              <th key={s} className="text-right px-3 py-2 text-muted-foreground font-medium">
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metricKeys.map((metric) => (
            <tr key={metric} className="border-t border-border/30">
              <td className="px-3 py-1.5 text-foreground/80">{metric.replace(/_/g, " ")}</td>
              {systems.map((s) => {
                const val = comparison[s]?.[metric];
                return (
                  <td key={s} className="text-right px-3 py-1.5 tabular-nums text-muted-foreground">
                    {val !== undefined
                      ? metric.includes("latency")
                        ? `${val.toFixed(0)}ms`
                        : val.toFixed(3)
                      : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
