
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
    <div className="space-y-4">
      {!health ? (
        <p className="text-xs text-muted-foreground">Loading...</p>
      ) : (
        <>
          {health.components.map((comp) => (
            <div
              key={comp.name}
              className="flex items-center justify-between p-3 rounded-xl bg-background/50 border border-border/50"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-2.5 h-2.5 rounded-full shadow-sm ${comp.status === "healthy"
                      ? "bg-emerald-500 shadow-emerald-500/50"
                      : "bg-red-500 shadow-red-500/50"
                    }`}
                />
                <span className="text-sm font-medium text-foreground">{comp.name}</span>
              </div>
              <span className="text-xs font-mono text-muted-foreground bg-secondary/50 px-2 py-1 rounded-md">
                {comp.response_time_ms != null
                  ? `${comp.response_time_ms}ms`
                  : comp.status}
              </span>
            </div>
          ))}
          <div className="pt-4 mt-4 border-t border-border/50 flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground font-medium flex items-center gap-2"><Activity size={14} /> Version</span>
              <span className="text-foreground font-mono bg-secondary/50 px-2 py-0.5 rounded-md text-xs">
                {health.version}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground font-medium flex items-center gap-2"><Activity size={14} /> Uptime</span>
              <span className="text-foreground">
                {formatUptime(health.uptime_seconds)}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
