import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { GraphViewer } from "@/components/GraphViewer";
import { CypherPanel } from "@/components/CypherPanel";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { queryGraph } from "@/lib/api";
import { ApiError } from "@/types/api";
import type { SeedNode, GraphNode, GraphEdge, PipelineMetadata, TraversalStep } from "@/types/api";
import { AlertCircle, MessageSquareText } from "lucide-react";

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
  const [traversalPath, setTraversalPath] = useState<TraversalStep[]>([]);
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
    setTraversalPath([]);
    setSelectedNodeId(null);

    try {
      const response = await queryGraph(question);
      setAnswer(response.answer);
      setSeedNodes(response.seed_nodes);
      setNodes(response.nodes);
      setEdges(response.edges);
      setCypher(response.cypher_used);
      setTraversalPath(response.traversal_path ?? []);
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
    <div className="flex-1 flex flex-col min-h-0 bg-background/50">
      {/* White curtain drop header */}
      <div className="bg-background/20 backdrop-blur-md border-b border-border/50 shadow-sm z-10 shrink-0">
        <div className="max-w-[1920px] mx-auto w-full px-4 md:px-8 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <MessageSquareText size={20} />
            </div>
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-bold tracking-tight text-foreground mt-0.5">Graph Query</h1>
              <span className="text-muted-foreground text-sm hidden sm:inline-block border-l border-border/50 pl-3">
                Ask natural language questions to interact with your knowledge graph.
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 p-4 md:p-8 flex flex-col gap-6 min-h-0 max-w-[1920px] mx-auto w-full">
        {/* Error banner */}
        {error && (
          <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-500 font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-2 shrink-0">
            <AlertCircle size={16} className="shrink-0" />
            {error}
          </div>
        )}

        {/* Main layout */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(360px,2fr)_3fr] gap-6 min-h-0">
          {/* Left: Chat */}
          <div className="flex flex-col min-h-0 overflow-hidden rounded-2xl border border-border/50 bg-card/40 backdrop-blur-sm shadow-sm">
            <div className="flex-1 flex flex-col min-h-0 p-4 md:p-6 custom-scrollbar overflow-y-auto">
              <ChatPanel
                onSubmit={handleSubmit}
                answer={answer}
                seedNodes={seedNodes}
                traversalPath={traversalPath}
                isLoading={isLoading}
                latencyMs={latencyMs ?? undefined}
                metadata={metadata}
                exampleQuestions={EXAMPLE_QUESTIONS}
              />
            </div>
          </div>

          {/* Right: Graph + Cypher */}
          <div className="flex flex-col gap-4 min-h-0">
            <div className="relative flex-1 overflow-hidden rounded-2xl border border-border/50 bg-card/40 backdrop-blur-sm shadow-sm">
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
              <div className="rounded-2xl border border-border/50 bg-card/40 backdrop-blur-sm p-4 shadow-sm shrink-0">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-primary">Generated Cypher</h3>
                <CypherPanel cypher={cypher} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
