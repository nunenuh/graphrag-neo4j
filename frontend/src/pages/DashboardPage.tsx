import { useState, useEffect } from "react";
import { StatsCards } from "@/components/StatsCards";
import { SchemaViewer } from "@/components/SchemaViewer";
import { SystemHealth } from "@/components/SystemHealth";
import { QuickActions } from "@/components/QuickActions";
import { Separator } from "@/components/ui/separator";
import { fetchGraphStats, fetchSchema, checkHealth } from "@/lib/api";
import type { GraphStats, SchemaResponse, HealthResponse } from "@/types/api";

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
    <div className="flex-1 overflow-auto p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          Knowledge Graph Overview
        </h2>
        <p className="text-sm text-muted-foreground">
          System status and graph statistics at a glance
        </p>
      </div>

      <StatsCards stats={stats} />

      <Separator className="opacity-50" />

      <div className="grid grid-cols-2 gap-4">
        <SchemaViewer schema={schema} />
        <SystemHealth health={health} />
      </div>

      <Separator className="opacity-50" />

      <div>
        <p className="text-sm font-medium text-foreground mb-3">Quick Actions</p>
        <QuickActions />
      </div>
    </div>
  );
}
