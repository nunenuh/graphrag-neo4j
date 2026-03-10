import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricCards } from "@/components/MetricCards";
import { CategoryBreakdown } from "@/components/CategoryBreakdown";
import { QueryDrillDown } from "@/components/QueryDrillDown";
import { fetchLatestReport, runEvaluation } from "@/lib/api";
import type { EvalReport } from "@/types/api";
import { Loader2, FlaskConical, Sparkles, AlertTriangle } from "lucide-react";

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
    <div className="flex-1 flex flex-col min-h-0 bg-background/50">
      {/* White curtain drop header */}
      <div className="bg-background/20 backdrop-blur-md border-b border-border/50 shadow-sm z-10 shrink-0">
        <div className="max-w-[1920px] mx-auto w-full px-4 md:px-8 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <FlaskConical size={20} />
            </div>
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-bold tracking-tight text-foreground mt-0.5">Evaluation Dashboard</h1>
              <span className="text-muted-foreground text-sm hidden sm:inline-block border-l border-border/50 pl-3">
                Benchmark RAG answer accuracy and latency.
              </span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            {categories.length > 0 && (
              <div className="relative">
                <select
                  value={categoryFilter ?? ""}
                  onChange={(e) => setCategoryFilter(e.target.value || null)}
                  className="appearance-none w-full sm:w-40 bg-background border border-border/50 text-foreground text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-1 focus:ring-primary/50 transition-colors shadow-sm"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground">
                  <svg className="h-4 w-4" opacity="0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            )}
            <button
              onClick={handleRunEvaluation}
              disabled={isRunning}
              className="group relative flex items-center justify-center gap-2 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground font-semibold shadow-sm hover:shadow disabled:opacity-50 transition-all overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              {isRunning ? (
                <Loader2 size={16} className="animate-spin relative z-10" />
              ) : (
                <Sparkles size={16} className="relative z-10" />
              )}
              <span className="relative z-10">{isRunning ? "Running..." : "Run Evaluation"}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 p-4 md:px-8 md:py-6 flex flex-col gap-4 min-h-0 max-w-[1920px] mx-auto w-full">
        {error && (
          <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-500 font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-2 shrink-0">
            <AlertTriangle size={16} className="shrink-0" />
            {error}
          </div>
        )}

        {!report ? (
          <div className="flex-1 flex items-center justify-center min-h-[300px]">
            <div className="text-center space-y-4 max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-secondary/30 flex items-center justify-center mx-auto mb-4 border border-border/50">
                <FlaskConical size={32} className="text-muted-foreground/50" />
              </div>
              <h3 className="text-lg font-medium text-foreground">No Evaluation Data</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                There is no existing evaluation report cached. Click the "Run Evaluation" button above to execute the benchmark suite.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0 bg-card/40 border border-border/50 rounded-2xl overflow-hidden backdrop-blur-sm shadow-sm shadow-black/5">
            <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
              <div className="border-b border-border/50 bg-card/60 px-4 py-3">
                <TabsList className="bg-background/80 border border-border/50 h-10 p-1">
                  <TabsTrigger value="overview" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">Overview</TabsTrigger>
                  <TabsTrigger value="baselines" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">Baselines</TabsTrigger>
                  <TabsTrigger value="queries" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">Queries</TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-auto p-4 md:p-6 custom-scrollbar">
                {/* Overview Tab */}
                <TabsContent value="overview" className="m-0 h-full flex flex-col gap-6">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground bg-background/50 border border-border/50 rounded-lg px-4 py-2 w-fit">
                    <span className="font-medium text-primary">System: {report.system_name}</span>
                    <span className="w-1 h-1 rounded-full bg-border/80"></span>
                    <span>Queries: {report.successful_queries} / {report.total_queries}</span>
                    <span className="w-1 h-1 rounded-full bg-border/80"></span>
                    <span>{new Date(report.timestamp).toLocaleString()}</span>
                  </div>

                  <div className="space-y-6">
                    <MetricCards metrics={report.metrics_summary} />
                    <CategoryBreakdown metricsByCategory={report.metrics_by_category} />
                  </div>

                  {report.failures.length > 0 && (
                    <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 mt-2">
                      <div className="flex items-center gap-2 text-red-500 mb-3">
                        <AlertTriangle size={16} />
                        <h3 className="text-sm font-semibold">
                          Failures ({report.failures.length})
                        </h3>
                      </div>
                      <ul className="text-xs text-red-500/80 space-y-1.5 pl-6 list-disc">
                        {report.failures.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </TabsContent>

                {/* Baselines Tab */}
                <TabsContent value="baselines" className="m-0 h-full">
                  {report.comparison ? (
                    <BaselineTable comparison={report.comparison} />
                  ) : (
                    <div className="flex flex-col items-center justify-center min-h-[200px] text-muted-foreground border border-dashed border-border/50 rounded-xl bg-background/30">
                      <p className="text-sm">No baseline comparison available.</p>
                      <p className="text-xs mt-1">Run evaluation with a baseline system to view comparisons.</p>
                    </div>
                  )}
                </TabsContent>

                {/* Queries Tab */}
                <TabsContent value="queries" className="m-0 h-full">
                  <QueryDrillDown results={report.results} categoryFilter={categoryFilter} />
                </TabsContent>
              </div>
            </Tabs>
          </div>
        )}
      </div>
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
