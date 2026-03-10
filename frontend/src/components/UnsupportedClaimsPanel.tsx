import { AlertTriangle } from "lucide-react";

interface UnsupportedClaimsPanelProps {
  claims: string[];
}

export function UnsupportedClaimsPanel({ claims }: UnsupportedClaimsPanelProps) {
  if (!claims || claims.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2.5 space-y-1.5">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
        <AlertTriangle size={12} className="shrink-0" />
        <span>Unsupported Claims ({claims.length})</span>
      </div>
      <ul className="space-y-1 pl-5">
        {claims.map((claim, i) => (
          <li key={i} className="text-[11px] text-amber-700/80 dark:text-amber-300/70 list-disc">
            {claim}
          </li>
        ))}
      </ul>
    </div>
  );
}
