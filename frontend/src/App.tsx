import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { GraphViewer } from "@/components/GraphViewer";
import { CypherPanel } from "@/components/CypherPanel";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { queryGraph } from "@/lib/api";
import { ApiError } from "@/types/api";
import type { SeedNode, GraphNode, GraphEdge } from "@/types/api";
import { AlertCircle, Network } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { StatusBadges } from "@/components/StatusBadges";

const EXAMPLE_QUESTIONS = [
  "What methods are used for object detection?",
  "Which papers introduced transformer architectures?",
  "What datasets are used to benchmark image classification?",
  "How does BERT relate to other NLP methods?",
];

export default function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [seedNodes, setSeedNodes] = useState<SeedNode[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [cypher, setCypher] = useState("");
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const handleSubmit = async (question: string) => {
    setIsLoading(true);
    setError(null);
    setAnswer("");
    setSeedNodes([]);
    setNodes([]);
    setEdges([]);
    setCypher("");
    setLatencyMs(null);
    setSelectedNodeId(null);

    try {
      const response = await queryGraph(question);
      setAnswer(response.answer);
      setSeedNodes(response.seed_nodes);
      setNodes(response.nodes);
      setEdges(response.edges);
      setCypher(response.cypher_used);
      setLatencyMs(response.latency_ms);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API error (${err.statusCode}): ${err.detail}`);
      } else {
        setError("Network error. Is the backend running?");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const seedNodeIds = new Set(seedNodes.map((sn) => sn.id));

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  const selectedNode = selectedNodeId
    ? nodes.find((n) => (n.uid || n.id) === selectedNodeId) ?? null
    : null;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="relative z-10 border-b border-border/50 backdrop-blur-sm bg-background/80">
        <div className="px-6 py-3 flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20">
            <Network size={18} className="text-primary" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              graphrag-neo4j
            </h1>
            <p className="text-[11px] text-muted-foreground leading-none">
              Graph RAG over ML Research Papers
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <StatusBadges />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-3 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-2">
          <AlertCircle size={14} className="text-destructive mt-0.5 shrink-0" />
          <p className="text-xs text-destructive">{error}</p>
        </div>
      )}

      {/* Main layout */}
      <div
        className="flex-1 p-3 grid grid-cols-[minmax(360px,2fr)_3fr] gap-3"
        style={{ height: "calc(100vh - 57px)" }}
      >
        {/* Left: Chat */}
        <div className="flex flex-col overflow-hidden rounded-xl border border-border/50 bg-card">
          <div className="flex-1 flex flex-col p-4">
            <ChatPanel
              onSubmit={handleSubmit}
              answer={answer}
              seedNodes={seedNodes}
              isLoading={isLoading}
              latencyMs={latencyMs ?? undefined}
              exampleQuestions={EXAMPLE_QUESTIONS}
            />
          </div>
        </div>

        {/* Right: Graph + Cypher */}
        <div className="flex flex-col gap-2 min-h-0">
          <div className="relative flex-1 overflow-hidden rounded-xl border border-border/50 bg-[hsl(var(--graph-bg))]">
            <GraphViewer
              nodes={nodes}
              edges={edges}
              seedNodeIds={seedNodeIds}
              onNodeSelect={handleNodeSelect}
            />
            {selectedNode && (
              <NodeDetailPanel
                node={selectedNode}
                edges={edges}
                allNodes={nodes}
                isSeed={seedNodeIds.has(selectedNodeId!)}
                onClose={() => setSelectedNodeId(null)}
                onNodeSelect={(id) => setSelectedNodeId(id)}
              />
            )}
          </div>
          {cypher && (
            <div className="rounded-xl border border-border/50 bg-card p-2">
              <CypherPanel cypher={cypher} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
