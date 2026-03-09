import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { GraphViewer } from "@/components/GraphViewer";
import { CypherPanel } from "@/components/CypherPanel";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { queryGraph } from "@/lib/api";
import { ApiError } from "@/types/api";
import type { SeedNode, GraphNode, GraphEdge, PipelineMetadata } from "@/types/api";
import { AlertCircle } from "lucide-react";

const EXAMPLE_QUESTIONS = [
  "What methods are used for object detection?",
  "Which papers introduced transformer architectures?",
  "What datasets are used to benchmark image classification?",
  "How does BERT relate to other NLP methods?",
];

export default function QueryPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [seedNodes, setSeedNodes] = useState<SeedNode[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [cypher, setCypher] = useState("");
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [metadata, setMetadata] = useState<PipelineMetadata | null>(null);
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
    setMetadata(null);
    setSelectedNodeId(null);

    try {
      const response = await queryGraph(question);
      setAnswer(response.answer);
      setSeedNodes(response.seed_nodes);
      setNodes(response.nodes);
      setEdges(response.edges);
      setCypher(response.cypher_used);
      setLatencyMs(response.latency_ms);
      setMetadata(response.metadata);
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
    <div className="flex-1 flex flex-col min-h-0">
      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-3 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-2">
          <AlertCircle size={14} className="text-destructive mt-0.5 shrink-0" />
          <p className="text-xs text-destructive">{error}</p>
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 p-3 grid grid-cols-[minmax(360px,2fr)_3fr] gap-3 min-h-0">
        {/* Left: Chat */}
        <div className="flex flex-col overflow-hidden rounded-xl border border-border/50 bg-card">
          <div className="flex-1 flex flex-col p-4">
            <ChatPanel
              onSubmit={handleSubmit}
              answer={answer}
              seedNodes={seedNodes}
              isLoading={isLoading}
              latencyMs={latencyMs ?? undefined}
              metadata={metadata}
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
