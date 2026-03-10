import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CommunityList } from "@/components/CommunityList";
import { TrendingChart } from "@/components/TrendingChart";
import { CentralityTable } from "@/components/CentralityTable";
import { runAnalytics, fetchCommunities, fetchTrends } from "@/lib/api";
import type {
  Community,
  CommunityMember,
  TrendingItem,
} from "@/types/api";
import { Loader2, BarChart3, Sparkles, Users, Network, TrendingUp, CheckCircle2 } from "lucide-react";

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
                  <BarChart3 size={24} />
                </div>
                <h1 className="text-3xl font-bold tracking-tight">Graph Analytics</h1>
              </div>
              <p className="text-muted-foreground text-sm max-w-xl leading-relaxed mt-3">
                Run advanced algorithms over the knowledge graph to detect latent communities, identify trending nodes, and calculate graph centrality metrics.
              </p>
            </div>

            <button
              onClick={handleRunAnalytics}
              disabled={isRunning || isLoading}
              className="group relative flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold shadow-[0_0_20px_-5px_hsl(var(--primary)/0.4)] hover:shadow-[0_0_25px_-5px_hsl(var(--primary)/0.6)] disabled:opacity-50 transition-all overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              {isRunning ? (
                <Loader2 size={18} className="animate-spin relative z-10" />
              ) : (
                <Sparkles size={18} className="relative z-10" />
              )}
              <span className="relative z-10 tracking-wide">{isRunning ? "Computing Algorithms..." : "Run Analytics Pipeline"}</span>
            </button>
          </div>

          {runMessage && (
            <div className="mt-6 px-4 py-3 rounded-xl bg-green-500/10 border border-green-500/20 text-sm text-green-500 font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
              <CheckCircle2 size={16} className="shrink-0" />
              {runMessage}
            </div>
          )}
        </div>

        {/* Highlight Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-card/50 border-border/50 backdrop-blur-sm shadow-sm hover:bg-card/80 transition-all duration-300 group">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">Detected Communities</CardTitle>
              <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500">
                <Users size={16} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold tracking-tight">{totalCommunities}</div>
              <p className="text-xs text-muted-foreground mt-2">Clusters found in graph</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50 backdrop-blur-sm shadow-sm hover:bg-card/80 transition-all duration-300 group">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">Highest Centrality</CardTitle>
              <div className="p-2 bg-purple-500/10 rounded-lg text-purple-500">
                <Network size={16} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold truncate h-10 flex items-center">
                {centralityMembers[0]?.name || "—"}
              </div>
              <p className="text-xs text-muted-foreground mt-2">Top PageRank entity</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50 backdrop-blur-sm shadow-sm hover:bg-card/80 transition-all duration-300 group">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">Total Trends</CardTitle>
              <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
                <TrendingUp size={16} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold tracking-tight">{methodTrends.length + taskTrends.length}</div>
              <p className="text-xs text-muted-foreground mt-2">Active monitored nodes</p>
            </CardContent>
          </Card>
        </div>

        {/* Loading state */}
        {isLoading && communities.length === 0 && (
          <div className="flex-1 flex items-center justify-center min-h-[200px]">
            <Loader2 size={32} className="animate-spin text-primary/50" />
          </div>
        )}

        {/* Main Content Area */}
        {!isLoading && communities.length > 0 && (
          <div className="flex-1 flex flex-col min-h-0 bg-card/40 border border-border/50 rounded-2xl overflow-hidden backdrop-blur-sm shadow-sm shadow-black/5">
            <Tabs defaultValue="communities" className="flex-1 flex flex-col min-h-0">
              <div className="border-b border-border/50 bg-card/60 px-4 py-3">
                <TabsList className="bg-background/80 border border-border/50 h-10 p-1">
                  <TabsTrigger value="communities" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">
                    Communities
                  </TabsTrigger>
                  <TabsTrigger value="trends" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">
                    Trends Display
                  </TabsTrigger>
                  <TabsTrigger value="centrality" className="text-xs px-6 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm rounded-md transition-all">
                    Node Centrality
                  </TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-auto p-4 md:p-6 custom-scrollbar">
                <TabsContent value="communities" className="m-0 h-full">
                  <CommunityList
                    communities={communities}
                    totalCommunities={totalCommunities}
                  />
                </TabsContent>

                <TabsContent value="trends" className="m-0 h-full">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="p-6 rounded-2xl border border-border/50 bg-background/50">
                      <TrendingChart
                        title="Emerging Methods"
                        items={methodTrends}
                        color="hsl(var(--primary))"
                      />
                    </div>
                    <div className="p-6 rounded-2xl border border-border/50 bg-background/50">
                      <TrendingChart
                        title="Trending Tasks"
                        items={taskTrends}
                        color="#a855f7"
                      />
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="centrality" className="m-0 h-full">
                  <CentralityTable members={centralityMembers} />
                </TabsContent>
              </div>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
}
