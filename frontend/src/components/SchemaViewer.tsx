
import { GitBranch, Tag } from "lucide-react";
import type { SchemaResponse } from "@/types/api";

const LABEL_COLORS: Record<string, string> = {
  Paper: "bg-blue-500",
  Method: "bg-emerald-500",
  Task: "bg-purple-500",
  Dataset: "bg-orange-500",
  Author: "bg-pink-500",
};

interface SchemaViewerProps {
  schema: SchemaResponse | null;
}

export function SchemaViewer({ schema }: SchemaViewerProps) {
  return (
    <div className="space-y-6">
      {!schema ? (
        <p className="text-xs text-muted-foreground animate-pulse">Loading schema...</p>
      ) : (
        <>
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Tag size={12} /> Node Labels
            </h3>
            <div className="flex flex-wrap gap-2">
              {schema.node_labels.map((label) => (
                <span
                  key={label}
                  className="flex items-center gap-2 text-sm text-foreground bg-background/50 border border-border/50 px-3 py-1.5 rounded-lg shadow-sm"
                >
                  <span
                    className={`w-2.5 h-2.5 rounded-full shadow-sm ${LABEL_COLORS[label] ?? "bg-gray-500 shadow-gray-500/50"}`}
                    style={LABEL_COLORS[label] ? { boxShadow: `0 0 8px var(--tw-shadow-color)` } : {}}
                  />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <GitBranch size={12} /> Relationships
            </h3>
            <div className="flex flex-wrap gap-2">
              {schema.relationship_types.map((rel) => (
                <span
                  key={rel}
                  className="flex items-center gap-1.5 text-xs font-medium text-foreground bg-secondary/30 border border-border/50 px-2.5 py-1 rounded-md"
                >
                  <GitBranch size={12} className="text-muted-foreground" />
                  {rel}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
