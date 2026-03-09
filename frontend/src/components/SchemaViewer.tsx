import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Tag size={14} className="text-muted-foreground" />
          Graph Schema
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!schema ? (
          <p className="text-xs text-muted-foreground">Loading...</p>
        ) : (
          <>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Node Labels
              </p>
              <div className="flex flex-wrap gap-2">
                {schema.node_labels.map((label) => (
                  <span
                    key={label}
                    className="flex items-center gap-1.5 text-xs text-foreground"
                  >
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${LABEL_COLORS[label] ?? "bg-gray-500"}`}
                    />
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Relationships
              </p>
              <div className="flex flex-wrap gap-2">
                {schema.relationship_types.map((rel) => (
                  <span
                    key={rel}
                    className="flex items-center gap-1.5 text-xs text-foreground"
                  >
                    <GitBranch size={12} className="text-muted-foreground" />
                    {rel}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
