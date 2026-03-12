import { useState, useEffect } from "react";
import { StatsCards } from "@/components/StatsCards";
import { SchemaViewer } from "@/components/SchemaViewer";
import { SystemHealth } from "@/components/SystemHealth";
import { QuickActions } from "@/components/QuickActions";

import { fetchGraphStats, fetchSchema, checkHealth } from "@/lib/api";
import type { GraphStats, SchemaResponse, HealthResponse } from "@/types/api";
import { LayoutDashboard } from "lucide-react";

export default function DashboardPage() {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchGraphStats().then(setStats).catch(() => setStats(null));
    fetchSchema().then(setSchema).catch(() => setSchema(null));
    checkHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-background/50 overflow-auto custom-scrollbar">
      {/* White curtain drop header */}
      <div className="bg-background/20 backdrop-blur-md border-b border-border/50 shadow-sm z-10 shrink-0">
        <div className="max-w-[1920px] mx-auto w-full px-4 md:px-8 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <LayoutDashboard size={20} />
            </div>
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-bold tracking-tight text-foreground mt-0.5">System Dashboard</h1>
              <span className="text-muted-foreground text-sm hidden sm:inline-block border-l border-border/50 pl-3">
                Monitor statistics, database schema, and service health.
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 p-4 md:px-8 md:py-6 max-w-[1920px] mx-auto w-full">
        <div className="flex flex-col gap-4">
          <StatsCards stats={stats} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card/40 border border-border/50 rounded-2xl p-6 backdrop-blur-sm shadow-sm overflow-hidden flex flex-col">
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">Database Schema</h2>
              <div className="flex-1 overflow-auto -mx-2 px-2 custom-scrollbar">
                <SchemaViewer schema={schema} />
              </div>
            </div>

            <div className="bg-card/40 border border-border/50 rounded-2xl p-6 backdrop-blur-sm shadow-sm">
              <h2 className="text-sm font-semibold mb-4">System Health</h2>
              <SystemHealth health={health} />
            </div>
          </div>

          <div className="bg-card/40 border border-border/50 rounded-2xl p-6 backdrop-blur-sm shadow-sm">
            <h2 className="text-sm font-semibold mb-4">Quick Actions</h2>
            <QuickActions />
          </div>
        </div>
      </div>
    </div>
  );
}
