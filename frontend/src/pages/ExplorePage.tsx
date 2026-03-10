import { useState, useCallback, useEffect } from "react";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";
import { ExploreControls } from "@/components/ExploreControls";
import { GraphViewer } from "@/components/GraphViewer";
import { NodeDetailPanel } from "@/components/NodeDetailPanel";
import { searchNodes, exploreGraph, fetchNodeDetail } from "@/lib/api";
import type {
  SearchResult,
  NodeDetail,
  GraphNode,
  GraphEdge,
  ExploreResponse,
} from "@/types/api";
import { Compass } from "lucide-react";

const EMPTY_SEED = new Set<string>();

export default function ExplorePage() {
  // Search state
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedUid, setSelectedUid] = useState<string | null>(null);

  // Explore graph state
  const [limit, setLimit] = useState(50);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  // Node detail state
  const [nodeDetail, setNodeDetail] = useState<NodeDetail | null>(null);
  const [, setSelectedNodeId] = useState<string | null>(null);

  // Load explore graph on mount and when limit changes
  const loadGraph = useCallback(async () => {
    setIsLoadingGraph(true);
    try {
      const data: ExploreResponse = await exploreGraph(limit);
      setNodes(
        data.nodes.map((n: any) => ({
          id: n.id || n.uid,
          uid: n.uid || n.id,
          label: n.label,
          name: n.name,
        })),
      );
      setEdges(
        data.edges.map((e) => ({
          from_id: e.from_id,
          to_id: e.to_id,
          type: e.type,
          properties: {},
        })),
      );
    } catch {
      // Silently fail — graph stays empty
    } finally {
      setIsLoadingGraph(false);
    }
  }, [limit]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Search handler
  const handleSearch = useCallback(
    async (query: string, label: string | undefined) => {
      setIsSearching(true);
      try {
        const resp = await searchNodes(query, label);
        setSearchResults(resp.results);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    },
    [],
  );

  // Select a search result — fetch detail and highlight in graph
  const handleResultSelect = useCallback(async (uid: string) => {
    setSelectedUid(uid);
    setSelectedNodeId(uid);
    try {
      const detail = await fetchNodeDetail(uid);
      setNodeDetail(detail);
    } catch {
      setNodeDetail(null);
    }
  }, []);

  // Select a node from the graph viewer
  const handleNodeSelect = useCallback(
    async (nodeId: string | null) => {
      setSelectedNodeId(nodeId);
      if (!nodeId) {
        setNodeDetail(null);
        return;
      }
      setSelectedUid(nodeId);
      try {
        const detail = await fetchNodeDetail(nodeId);
        setNodeDetail(detail);
      } catch {
        setNodeDetail(null);
      }
    },
    [],
  );

  // Navigate to a related node from the detail panel
  const handleDetailNodeSelect = useCallback(
    (id: string) => {
      handleNodeSelect(id);
    },
    [handleNodeSelect],
  );

  // Build a GraphNode for NodeDetailPanel from nodeDetail
  const selectedGraphNode: GraphNode | null = nodeDetail
    ? {
      id: nodeDetail.uid,
      uid: nodeDetail.uid,
      label: nodeDetail.label as GraphNode["label"],
      name:
        (nodeDetail.properties.name as string) ||
        (nodeDetail.properties.title as string) ||
        nodeDetail.uid,
      ...nodeDetail.properties,
    }
    : null;

  // Build edges from nodeDetail for the panel
  const detailEdges: GraphEdge[] = nodeDetail
    ? [
      ...nodeDetail.outgoing.map((r) => ({
        from_id: nodeDetail.uid,
        to_id: r.to,
        type: r.type,
        properties: {} as Record<string, string>,
      })),
      ...nodeDetail.incoming.map((r) => ({
        from_id: r.from,
        to_id: nodeDetail.uid,
        type: r.type,
        properties: {} as Record<string, string>,
      })),
    ]
    : [];

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-background/50">
      <div className="flex-1 p-4 md:p-8 flex flex-col gap-6 min-h-0 max-w-[1400px] mx-auto w-full">
        {/* Modern Header Section */}
        <div className="relative overflow-hidden rounded-2xl border border-border/50 bg-gradient-to-br from-card to-secondary/30 p-6 md:p-8 shadow-sm shrink-0">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
          <div className="absolute -inset-y-0 right-0 w-1/3 bg-primary/5 blur-[100px] rounded-full pointer-events-none"></div>

          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2.5 bg-primary/10 rounded-xl text-primary">
                  <Compass size={24} />
                </div>
                <h1 className="text-3xl font-bold tracking-tight">Graph Explorer</h1>
              </div>
              <p className="text-muted-foreground text-sm max-w-xl leading-relaxed mt-3">
                Visualize and traverse the entire knowledge graph. Search for specific nodes or explore their connections and relationships recursively.
              </p>
            </div>
          </div>
        </div>

        {/* Main two-panel layout */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 min-h-0">
          {/* Left panel: Search + Results */}
          <div className="flex flex-col gap-4 min-h-0 overflow-hidden rounded-2xl border border-border/50 bg-card/40 backdrop-blur-sm shadow-sm">
            <div className="p-4 pb-0">
              <SearchBar onSearch={handleSearch} />
            </div>
            {isSearching && (
              <p className="text-xs text-muted-foreground text-center py-4">
                Searching...
              </p>
            )}
            <div className="flex-1 px-4 pb-4 min-h-0 overflow-auto custom-scrollbar">
              <SearchResults
                results={searchResults}
                selectedUid={selectedUid}
                onSelect={handleResultSelect}
              />
            </div>
          </div>

          {/* Right panel: Controls + Graph + Detail */}
          <div className="flex flex-col min-h-0 overflow-hidden rounded-2xl border border-border/50 bg-card/40 backdrop-blur-sm shadow-sm relative">
            <ExploreControls
              limit={limit}
              onLimitChange={setLimit}
              onRefresh={loadGraph}
              isLoading={isLoadingGraph}
            />
            <div className="relative flex-1">
              <div className="absolute inset-0">
                <GraphViewer
                  nodes={nodes}
                  edges={edges}
                  seedNodeIds={EMPTY_SEED}
                  onNodeSelect={handleNodeSelect}
                  emptyMessage="Graph is empty. Nodes will load automatically."
                />
              </div>
              {selectedGraphNode && (
                <NodeDetailPanel
                  node={selectedGraphNode}
                  edges={detailEdges}
                  allNodes={nodes}
                  isSeed={false}
                  onClose={() => {
                    setSelectedNodeId(null);
                    setNodeDetail(null);
                  }}
                  onNodeSelect={handleDetailNodeSelect}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
