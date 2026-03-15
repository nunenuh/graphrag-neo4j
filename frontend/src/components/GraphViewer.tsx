import { useRef, useState, useMemo, useCallback, useEffect } from "react";
import { ZoomIn, ZoomOut, Maximize } from "lucide-react";
import { InteractiveNvlWrapper } from "@neo4j-nvl/react";
import type NVL from "@neo4j-nvl/base";
import type { Node, Relationship, HitTargets } from "@neo4j-nvl/base";
import type { MouseEventCallbacks } from "@neo4j-nvl/react";
import type { GraphNode, GraphEdge } from "@/types/api";

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  seedNodeIds: Set<string>;
  onNodeSelect?: (nodeId: string | null) => void;
  emptyMessage?: string;
}

const NODE_COLORS: Record<string, string> = {
  Paper: "#3b82f6",
  Method: "#22c55e",
  Task: "#a855f7",
  Dataset: "#f97316",
  Author: "#64748b",
  Repository: "#ec4899",
};

const DEFAULT_COLOR = "#64748b";
const REL_COLOR = "rgba(148, 163, 184, 0.5)";

export function GraphViewer({ nodes, edges, seedNodeIds, onNodeSelect, emptyMessage }: GraphViewerProps) {
  const nvlRef = useRef<NVL>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const { clientWidth: w, clientHeight: h } = el;
      if (w > 0 && h > 0) {
        setSize((prev) => (prev?.w === w && prev?.h === h ? prev : { w, h }));
      }
    };
    measure();
    const observer = new ResizeObserver(() => measure());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

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
          caption: name.length > 28 ? name.slice(0, 26) + "…" : name,
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
      onCanvasClick: () => { onNodeSelect?.(null); },
      onPan: true,
      onZoom: true,
      onDrag: true,
    }),
    [onNodeSelect],
  );

  const handleLayoutDone = useCallback(() => {
    nvlRef.current?.fit(nvlNodes.map((n) => n.id));
  }, [nvlNodes]);

  const labelCounts: Record<string, number> = {};
  for (const n of nodes) {
    const lbl = n.label || "Unknown";
    labelCounts[lbl] = (labelCounts[lbl] || 0) + 1;
  }

  const hasNodes = nodes.length > 0;
  const canRender = hasNodes && size !== null;
  return (
    <div
      ref={containerRef}
      className="nvl-container relative"
      style={{ width: "100%", height: "100%", position: "relative" }}
    >
      {!hasNodes && (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground p-4 text-center">
          <span className="text-sm bg-card/50 backdrop-blur-sm border border-border/50 py-2 px-4 rounded-xl shadow-sm">
            {emptyMessage || "Ask a question to see the knowledge graph"}
          </span>
        </div>
      )}

      {canRender && (
        <InteractiveNvlWrapper
          ref={nvlRef}
          nodes={nvlNodes}
          rels={nvlRels}
          mouseEventCallbacks={mouseCallbacks}
          style={{ width: size.w, height: size.h }}
          nvlOptions={{
            layout: "d3Force",
            initialZoom: 0.5,
            allowDynamicMinZoom: true,
            renderer: "canvas",
            styling: {
              defaultNodeColor: DEFAULT_COLOR,
              defaultRelationshipColor: REL_COLOR,
            },
          }}
          onInitializationError={(err) => console.error("NVL init error:", err)}
          nvlCallbacks={{
            onLayoutDone: handleLayoutDone,
          }}
        />
      )}

      {canRender && (
        <div className="absolute top-3 right-3 z-10 flex flex-col gap-1 p-1 rounded-lg border border-border/50 bg-card/90 backdrop-blur-sm shadow-sm">
          <button
            onClick={() => { const z = nvlRef.current?.getScale(); if (z) nvlRef.current?.setZoom(z * 1.5); }}
            className="p-1.5 hover:bg-secondary rounded-md text-muted-foreground hover:text-foreground transition-colors"
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={() => { const z = nvlRef.current?.getScale(); if (z) nvlRef.current?.setZoom(z / 1.5); }}
            className="p-1.5 hover:bg-secondary rounded-md text-muted-foreground hover:text-foreground transition-colors"
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={handleLayoutDone}
            className="p-1.5 hover:bg-secondary rounded-md text-muted-foreground hover:text-foreground transition-colors"
            title="Fit to screen"
          >
            <Maximize size={16} />
          </button>
        </div>
      )}

      {hasNodes && (
        <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1 px-2.5 py-2 rounded-lg border border-border/50 bg-card/90 backdrop-blur-sm shadow-sm">
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
      )}
    </div>
  );
}
