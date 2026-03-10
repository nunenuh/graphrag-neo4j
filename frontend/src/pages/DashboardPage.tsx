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
      <div className="flex flex-col gap-6 p-4 md:p-8 max-w-[1400px] mx-auto w-full">
        {/* Modern Header Section */}
        <div className="relative overflow-hidden rounded-2xl border border-border/50 bg-gradient-to-br from-card to-secondary/30 p-6 md:p-8 shadow-sm">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
          <div className="absolute -inset-y-0 right-0 w-1/3 bg-primary/5 blur-[100px] rounded-full pointer-events-none"></div>

          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2.5 bg-primary/10 rounded-xl text-primary">
                  <LayoutDashboard size={24} />
                </div>
                <h1 className="text-3xl font-bold tracking-tight">System Dashboard</h1>
              </div>
              <p className="text-muted-foreground text-sm max-w-xl leading-relaxed mt-3">
                Monitor knowledge graph statistics, service health status, and perform quick actions to manage your data sources.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-6">
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
