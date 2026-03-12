import { X, FileText, Cpu, Target, Database, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { GraphNode, GraphEdge } from "@/types/api";

interface NodeDetailPanelProps {
  node: GraphNode;
  edges: GraphEdge[];
  allNodes: GraphNode[];
  isSeed: boolean;
  onClose: () => void;
  onNodeSelect: (nodeId: string) => void;
}

const LABEL_CONFIG: Record<string, { icon: typeof FileText; color: string; badge: string }> = {
  Paper: {
    icon: FileText,
    color: "text-blue-500",
    badge: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  Method: {
    icon: Cpu,
    color: "text-emerald-500",
    badge: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  Task: {
    icon: Target,
    color: "text-purple-500",
    badge: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  },
  Dataset: {
    icon: Database,
    color: "text-orange-500",
    badge: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
  },
};

const HIDDEN_KEYS = new Set(["uid", "id", "name", "title", "label", "embedding", "created_at"]);

function MetadataRow({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="space-y-0.5">
      <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="text-xs text-foreground/90 leading-relaxed">
        <div className="max-h-48 overflow-y-auto custom-scrollbar pr-2 whitespace-pre-wrap break-words">
          {value}
        </div>
      </dd>
    </div>
  );
}

export function NodeDetailPanel({
  node,
  edges,
  allNodes,
  isSeed,
  onClose,
  onNodeSelect,
}: NodeDetailPanelProps) {
  const nodeId = node.uid || node.id;
  const label = node.label || "";
  const config = LABEL_CONFIG[label];
  const Icon = config?.icon ?? FileText;
  const name = node.name || node.title || nodeId;

  // Find connected edges
  const outgoing = edges.filter((e) => e.from_id === nodeId);
  const incoming = edges.filter((e) => e.to_id === nodeId);

  // Build node lookup for names
  const nodeMap = new Map(allNodes.map((n) => [n.uid || n.id, n]));

  // Collect extra properties (not in the known set)
  const extraProps = Object.entries(node).filter(
    ([k, v]) => !HIDDEN_KEYS.has(k) && v != null && v !== "",
  );

  return (
    <div className="absolute top-3 right-3 bottom-3 w-72 z-20 rounded-xl border border-border/50 bg-card/95 backdrop-blur-md shadow-xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-2.5 p-3 border-b border-border/40">
        <div className={`mt-0.5 ${config?.color ?? "text-muted-foreground"}`}>
          <Icon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">{name}</h3>
          <div className="flex items-center gap-1.5 mt-1">
            <Badge
              variant="outline"
              className={`text-[10px] py-0 ${config?.badge ?? "border-border"}`}
            >
              {label || "Node"}
            </Badge>
            {isSeed && (
              <Badge variant="outline" className="text-[10px] py-0 bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20">
                Seed
              </Badge>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-secondary/80 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-3">
          {/* Core fields by node type */}
          {label === "Paper" && (
            <>
              <MetadataRow label="Title" value={node.title as string ?? ""} />
              <MetadataRow label="Abstract" value={node.abstract as string ?? ""} />
              <MetadataRow label="Year" value={node.year as string ?? ""} />
              {node.url && (
                <div className="space-y-0.5">
                  <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    URL
                  </dt>
                  <dd>
                    <a
                      href={node.url as string}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                    >
                      Open paper <ExternalLink size={10} />
                    </a>
                  </dd>
                </div>
              )}
            </>
          )}

          {label === "Method" && (
            <>
              <MetadataRow label="Full Name" value={node.full_name as string ?? ""} />
              <MetadataRow label="Description" value={node.description as string ?? ""} />
            </>
          )}

          {label === "Task" && (
            <>
              <MetadataRow label="Area" value={node.area as string ?? ""} />
              <MetadataRow label="Description" value={node.description as string ?? ""} />
            </>
          )}

          {label === "Dataset" && (
            <>
              <MetadataRow label="Description" value={node.description as string ?? ""} />
              <MetadataRow label="Modalities" value={node.modalities as string ?? ""} />
            </>
          )}

          {/* Extra properties (catch-all) */}
          {extraProps
            .filter(([k]) => !["abstract", "year", "url", "full_name", "description", "area", "modalities"].includes(k))
            .map(([k, v]) => (
              <MetadataRow key={k} label={k.replace(/_/g, " ")} value={String(v)} />
            ))}

          {/* ID */}
          <MetadataRow label="UID" value={nodeId} />

          {/* Relationships */}
          {(outgoing.length > 0 || incoming.length > 0) && (
            <div className="space-y-2 pt-2 border-t border-border/30">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Relationships ({outgoing.length + incoming.length})
              </span>

              {outgoing.map((e, i) => {
                const target = nodeMap.get(e.to_id);
                const targetName = target?.name || target?.title || e.to_id;
                const targetLabel = target?.label || "";
                const targetConfig = LABEL_CONFIG[targetLabel];
                return (
                  <button
                    key={`out-${i}`}
                    onClick={() => onNodeSelect(e.to_id)}
                    className="flex items-center gap-1.5 w-full text-left group"
                  >
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      &rarr; {e.type}
                    </span>
                    <span className={`text-xs truncate group-hover:underline ${targetConfig?.color ?? "text-foreground/80"}`}>
                      {targetName}
                    </span>
                    {e.properties && Object.keys(e.properties).length > 0 && (
                      <span className="text-[9px] text-muted-foreground/60 shrink-0">
                        ({Object.entries(e.properties).map(([k, v]) => `${k}: ${v}`).join(", ")})
                      </span>
                    )}
                  </button>
                );
              })}

              {incoming.map((e, i) => {
                const source = nodeMap.get(e.from_id);
                const sourceName = source?.name || source?.title || e.from_id;
                const sourceLabel = source?.label || "";
                const sourceConfig = LABEL_CONFIG[sourceLabel];
                return (
                  <button
                    key={`in-${i}`}
                    onClick={() => onNodeSelect(e.from_id)}
                    className="flex items-center gap-1.5 w-full text-left group"
                  >
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      &larr; {e.type}
                    </span>
                    <span className={`text-xs truncate group-hover:underline ${sourceConfig?.color ?? "text-foreground/80"}`}>
                      {sourceName}
                    </span>
                    {e.properties && Object.keys(e.properties).length > 0 && (
                      <span className="text-[9px] text-muted-foreground/60 shrink-0">
                        ({Object.entries(e.properties).map(([k, v]) => `${k}: ${v}`).join(", ")})
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
