import { useEffect, useState } from "react";
import { pingBackend, pingNeo4j } from "@/lib/api";

type ServiceStatus = "loading" | "healthy" | "unhealthy";

interface StatusState {
  backend: ServiceStatus;
  neo4j: ServiceStatus;
  neo4jLatency: number | null;
}

const INITIAL: StatusState = { backend: "loading", neo4j: "loading", neo4jLatency: null };

export function StatusBadges() {
  const [status, setStatus] = useState<StatusState>(INITIAL);

  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      // Backend ping
      const backendOk = await pingBackend()
        .then(() => true)
        .catch(() => false);

      if (!mounted) return;

      if (!backendOk) {
        setStatus({ backend: "unhealthy", neo4j: "unhealthy", neo4jLatency: null });
        return;
      }

      // Neo4j ping (separate endpoint)
      try {
        const neo4jRes = await pingNeo4j();
        if (!mounted) return;
        setStatus({
          backend: "healthy",
          neo4j: neo4jRes.status === "healthy" ? "healthy" : "unhealthy",
          neo4jLatency: neo4jRes.response_time_ms,
        });
      } catch {
        if (!mounted) return;
        setStatus({ backend: "healthy", neo4j: "unhealthy", neo4jLatency: null });
      }
    };

    poll();
    const interval = setInterval(poll, 30_000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <div className="flex items-center gap-1.5">
      <Indicator label="API" status={status.backend} />
      <Indicator
        label="Neo4j"
        status={status.neo4j}
        detail={status.neo4jLatency != null ? `${status.neo4jLatency}ms` : undefined}
      />
    </div>
  );
}

function Indicator({ label, status, detail }: { label: string; status: ServiceStatus; detail?: string }) {
  const color =
    status === "healthy"
      ? "bg-emerald-500"
      : status === "unhealthy"
        ? "bg-red-500"
        : "bg-yellow-500";

  const borderColor =
    status === "healthy"
      ? "border-emerald-500/20 bg-emerald-500/10"
      : status === "unhealthy"
        ? "border-red-500/20 bg-red-500/10"
        : "border-yellow-500/20 bg-yellow-500/10";

  const textColor =
    status === "healthy"
      ? "text-emerald-600 dark:text-emerald-400"
      : status === "unhealthy"
        ? "text-red-600 dark:text-red-400"
        : "text-yellow-600 dark:text-yellow-400";

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${borderColor}`}
      title={detail ? `${label}: ${detail}` : `${label}: ${status}`}
    >
      <div className={`w-1.5 h-1.5 rounded-full ${color} ${status === "loading" ? "animate-pulse" : ""}`} />
      <span className={`text-[10px] font-medium ${textColor}`}>{label}</span>
    </div>
  );
}
