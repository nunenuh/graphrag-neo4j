import { useRef, useMemo, useCallback } from "react";
import { InteractiveNvlWrapper } from "@neo4j-nvl/react";
import type { Node, Relationship, HitTargets } from "@neo4j-nvl/base";
import type { MouseEventCallbacks } from "@neo4j-nvl/react";
import type { GraphNode, GraphEdge } from "@/types/api";

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  seedNodeIds: Set<string>;
  onNodeSelect?: (nodeId: string | null) => void;
}

const NODE_COLORS: Record<string, string> = {
  Paper: "#3b82f6",   // blue
  Method: "#22c55e",  // green
  Task: "#a855f7",    // purple
  Dataset: "#f97316", // orange
};

const DEFAULT_COLOR = "#64748b";
const REL_COLOR = "rgba(148, 163, 184, 0.5)";

export function GraphViewer({ nodes, edges, seedNodeIds, onNodeSelect }: GraphViewerProps) {
  const nvlRef = useRef(null);

  const nvlNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => {
        const id = n.uid || n.id || "";
        const isSeed = seedNodeIds.has(id);
        const label = n.label || "";
        const name = n.name || n.title || id;
        const color = NODE_COLORS[label] ?? DEFAULT_COLOR;

        return {
          id,
          size: isSeed ? 35 : 22,
          color,
          caption: name.length > 28 ? name.slice(0, 26) + "\u2026" : name,
          activated: isSeed,
        };
      }),
    [nodes, seedNodeIds],
  );

  const nvlRels: Relationship[] = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `rel-${i}`,
        from: e.from_id,
        to: e.to_id,
        caption: e.type,
        color: REL_COLOR,
        width: 1.5,
      })),
    [edges],
  );

  const mouseCallbacks: MouseEventCallbacks = useMemo(
    () => ({
      onNodeClick: (node: Node, _ht: HitTargets, _evt: globalThis.MouseEvent) => {
        onNodeSelect?.(node.id);
      },
      onCanvasClick: () => {
        onNodeSelect?.(null);
      },
      onZoom: () => {},
      onPan: () => {},
    }),
    [onNodeSelect],
  );

  const handleLayoutDone = useCallback(() => {}, []);

  if (!nodes.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="opacity-30">
          <circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="6" cy="18" r="2" /><circle cx="18" cy="18" r="2" /><circle cx="12" cy="12" r="2" />
          <line x1="8" y1="6" x2="10" y2="10" /><line x1="14" y1="10" x2="16" y2="6" /><line x1="8" y1="18" x2="10" y2="14" /><line x1="14" y1="14" x2="16" y2="18" />
        </svg>
        <span className="text-sm">Ask a question to see the knowledge graph</span>
      </div>
    );
  }

  // Compute label distribution for legend
  const labelCounts: Record<string, number> = {};
  for (const n of nodes) {
    const lbl = n.label || "Unknown";
    labelCounts[lbl] = (labelCounts[lbl] || 0) + 1;
  }

  return (
    <div className="w-full h-full nvl-container relative">
      <InteractiveNvlWrapper
        ref={nvlRef}
        nodes={nvlNodes}
        rels={nvlRels}
        mouseEventCallbacks={mouseCallbacks}
        nvlOptions={{
          layout: "forceDirected",
          initialZoom: 1,
          renderer: "canvas",
          styling: {
            defaultNodeColor: DEFAULT_COLOR,
            defaultRelationshipColor: REL_COLOR,
          },
        }}
        nvlCallbacks={{
          onLayoutDone: handleLayoutDone,
        }}
      />

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-col gap-1 px-2.5 py-2 rounded-lg border border-border/50 bg-card/90 backdrop-blur-sm shadow-sm">
        {Object.entries(labelCounts).map(([label, count]) => (
          <div key={label} className="flex items-center gap-2 text-[10px]">
            <div
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: NODE_COLORS[label] ?? DEFAULT_COLOR }}
            />
            <span className="text-foreground/80 font-medium">{label}</span>
            <span className="text-muted-foreground/60 tabular-nums">{count}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 text-[10px] pt-0.5 border-t border-border/30">
          <div className="w-2.5 h-2.5 rounded-full shrink-0 border-2 border-foreground/40 bg-transparent" />
          <span className="text-muted-foreground">= seed node (larger)</span>
        </div>
      </div>
    </div>
  );
}
