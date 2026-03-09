import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";
import type { HealthResponse } from "@/types/api";

interface SystemHealthProps {
  health: HealthResponse | null;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function SystemHealth({ health }: SystemHealthProps) {
  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity size={14} className="text-muted-foreground" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!health ? (
          <p className="text-xs text-muted-foreground">Loading...</p>
        ) : (
          <>
            {health.components.map((comp) => (
              <div
                key={comp.name}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      comp.status === "healthy"
                        ? "bg-emerald-500"
                        : "bg-red-500"
                    }`}
                  />
                  <span className="text-xs text-foreground">{comp.name}</span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {comp.response_time_ms != null
                    ? `${comp.response_time_ms}ms`
                    : comp.status}
                </span>
              </div>
            ))}
            <div className="pt-2 border-t border-border/50 flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Version</span>
              <span className="text-xs text-foreground font-mono">
                {health.version}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Uptime</span>
              <span className="text-xs text-foreground">
                {formatUptime(health.uptime_seconds)}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
