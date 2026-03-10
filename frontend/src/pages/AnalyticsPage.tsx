import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CommunityList } from "@/components/CommunityList";
import { TrendingChart } from "@/components/TrendingChart";
import { CentralityTable } from "@/components/CentralityTable";
import { runAnalytics, fetchCommunities, fetchTrends } from "@/lib/api";
import type {
  Community,
  CommunityMember,
  TrendingItem,
} from "@/types/api";
import { Loader2, Play, BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const [communities, setCommunities] = useState<Community[]>([]);
  const [totalCommunities, setTotalCommunities] = useState(0);
  const [isLoadingCommunities, setIsLoadingCommunities] = useState(false);

  const [methodTrends, setMethodTrends] = useState<TrendingItem[]>([]);
  const [taskTrends, setTaskTrends] = useState<TrendingItem[]>([]);
  const [isLoadingTrends, setIsLoadingTrends] = useState(false);

  const [centralityMembers, setCentralityMembers] = useState<CommunityMember[]>([]);

  const loadCommunities = useCallback(async () => {
    setIsLoadingCommunities(true);
    try {
      const resp = await fetchCommunities(50);
      setCommunities(resp.communities);
      setTotalCommunities(resp.total_communities);

      // Extract all members with pagerank for centrality tab
      const allMembers: CommunityMember[] = [];
      for (const c of resp.communities) {
        for (const m of c.top_members) {
          if (m.pagerank !== undefined) {
            allMembers.push(m);
          }
        }
      }
      // Deduplicate by uid and sort by pagerank descending
      const seen = new Set<string>();
      const unique = allMembers.filter((m) => {
        if (seen.has(m.uid)) return false;
        seen.add(m.uid);
        return true;
      });
      unique.sort((a, b) => (b.pagerank ?? 0) - (a.pagerank ?? 0));
      setCentralityMembers(unique);
    } catch {
      // keep empty
    } finally {
      setIsLoadingCommunities(false);
    }
  }, []);

  const loadTrends = useCallback(async () => {
    setIsLoadingTrends(true);
    try {
      const [methods, tasks] = await Promise.all([
        fetchTrends("Method", 10),
        fetchTrends("Task", 10),
      ]);
      setMethodTrends(methods.items);
      setTaskTrends(tasks.items);
    } catch {
      // keep empty
    } finally {
      setIsLoadingTrends(false);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    loadCommunities();
    loadTrends();
  }, [loadCommunities, loadTrends]);

  const handleRunAnalytics = async () => {
    setIsRunning(true);
    setRunMessage(null);
    try {
      const resp = await runAnalytics();
      setRunMessage(resp.message);
      // Reload data after analytics run
      await Promise.all([loadCommunities(), loadTrends()]);
    } catch {
      setRunMessage("Failed to run analytics pipeline.");
    } finally {
      setIsRunning(false);
    }
  };

  const isLoading = isLoadingCommunities || isLoadingTrends;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 p-3 flex flex-col gap-3 min-h-0 max-w-5xl mx-auto w-full">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-primary" />
            <h1 className="text-lg font-semibold">Graph Analytics</h1>
          </div>
          <button
            onClick={handleRunAnalytics}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {isRunning ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Play size={12} />
            )}
            {isRunning ? "Running..." : "Run Analytics"}
          </button>
        </div>

        {runMessage && (
          <div className="px-3 py-2 rounded-lg bg-secondary/50 border border-border/50 text-xs text-muted-foreground">
            {runMessage}
          </div>
        )}

        {/* Loading state */}
        {isLoading && communities.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 size={20} className="animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="communities" className="flex-1 flex flex-col min-h-0">
          <TabsList className="w-fit">
            <TabsTrigger value="communities" className="text-xs">
              Communities
            </TabsTrigger>
            <TabsTrigger value="trends" className="text-xs">
              Trends
            </TabsTrigger>
            <TabsTrigger value="centrality" className="text-xs">
              Centrality
            </TabsTrigger>
          </TabsList>

          <TabsContent value="communities" className="flex-1 overflow-auto mt-2">
            <CommunityList
              communities={communities}
              totalCommunities={totalCommunities}
            />
          </TabsContent>

          <TabsContent value="trends" className="flex-1 overflow-auto mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TrendingChart
                title="Top Methods"
                items={methodTrends}
                color="#22c55e"
              />
              <TrendingChart
                title="Top Tasks"
                items={taskTrends}
                color="#a855f7"
              />
            </div>
          </TabsContent>

          <TabsContent value="centrality" className="flex-1 overflow-auto mt-2">
            <CentralityTable members={centralityMembers} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
