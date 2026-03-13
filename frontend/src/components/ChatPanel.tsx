import { useState, useRef, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2, Sparkles, Brain, GitBranch, FileText, Zap, ChevronDown, ChevronRight } from "lucide-react";
import type { SeedNode, PipelineMetadata, TraversalStep } from "@/types/api";
import { QueryTypeBadge } from "@/components/QueryTypeBadge";
import { RetrievalStrategyBadge } from "@/components/RetrievalStrategyBadge";
import { ProvenanceBadge } from "@/components/ProvenanceBadge";
import { UnsupportedClaimsPanel } from "@/components/UnsupportedClaimsPanel";
import { TraversalPath } from "@/components/TraversalPath";

const BADGE_COLORS: Record<string, string> = {
  Paper: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  Method: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  Task: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  Dataset: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
};

interface ChatPanelProps {
  onSubmit: (question: string) => void;
  answer: string;
  seedNodes: SeedNode[];
  traversalPath?: TraversalStep[];
  isLoading: boolean;
  latencyMs?: number;
  metadata: PipelineMetadata | null;
  exampleQuestions: string[];
}

export function ChatPanel({
  onSubmit,
  answer,
  seedNodes,
  traversalPath = [],
  isLoading,
  latencyMs,
  metadata,
  exampleQuestions,
}: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [showMetadata, setShowMetadata] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom whenever content updates
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [answer, seedNodes, metadata, showMetadata]);

  const handleSubmit = (q: string) => {
    if (!q.trim()) return;
    setQuestion(q);
    onSubmit(q.trim());
  };

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Example questions */}
      {!answer && !isLoading && (
        <div className="space-y-2.5">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
            <Sparkles size={11} />
            <span>Try an example</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {exampleQuestions.map((eq) => (
              <button
                key={eq}
                onClick={() => handleSubmit(eq)}
                disabled={isLoading}
                className="text-xs px-3 py-1.5 rounded-lg border border-border/60 bg-secondary/50 hover:bg-secondary text-muted-foreground hover:text-foreground transition-all duration-150 disabled:opacity-40"
              >
                {eq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && !answer && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 size={16} className="animate-spin text-primary" />
            <span>Searching knowledge graph...</span>
          </div>
        </div>
      )}

      {/* Seed node badges */}
      {seedNodes.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
            Seed nodes
          </span>
          <div className="flex flex-wrap gap-1.5">
            {seedNodes.map((sn) => (
              <Badge
                key={sn.id}
                variant="outline"
                className={`text-[11px] font-normal py-0.5 ${BADGE_COLORS[sn.label] ?? "border-border"}`}
              >
                {sn.name}
                <span className="ml-1.5 opacity-50 tabular-nums">{sn.score.toFixed(2)}</span>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Traversal path */}
      {traversalPath.length > 0 && (
        <TraversalPath steps={traversalPath} />
      )}

      {/* Answer */}
      {answer && (
        <ScrollArea className="flex-1 rounded-lg border border-border/40 bg-secondary/30">
          <div className="p-4 space-y-3">
            {/* Query type + retrieval strategy badges */}
            {metadata && (metadata.query_type || metadata.retrieval_strategy) && (
              <div className="flex items-center gap-2 flex-wrap">
                <QueryTypeBadge queryType={metadata.query_type} />
                <RetrievalStrategyBadge strategy={metadata.retrieval_strategy} />
              </div>
            )}

            <div className="text-[13px] leading-relaxed text-foreground/90 markdown-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 className="text-base font-bold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-[15px] font-bold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mb-2">{children}</h3>,
                  p: ({ children }) => <p className="mb-3 last:mb-0 text-foreground/90">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                  li: ({ children }) => <li>{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                  a: ({ children, href }) => <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                  code: ({ children }) => <code className="bg-muted px-1.5 py-0.5 rounded text-[11px] font-mono text-foreground/80">{children}</code>,
                }}
              >
                {answer}
              </ReactMarkdown>
            </div>

            {/* Provenance score */}
            {metadata?.provenance_score !== undefined && metadata?.provenance_score !== null && (
              <ProvenanceBadge score={metadata.provenance_score} />
            )}

            {/* Unsupported claims warning */}
            {metadata?.unsupported_claims && metadata.unsupported_claims.length > 0 && (
              <UnsupportedClaimsPanel claims={metadata.unsupported_claims} />
            )}

            {/* Pipeline Metadata */}
            {(latencyMs !== undefined || metadata) && (
              <div className="pt-2 border-t border-border/30 space-y-2">
                <button
                  onClick={() => setShowMetadata((v) => !v)}
                  className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showMetadata ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                  <span>Pipeline Details</span>
                  {latencyMs !== undefined && (
                    <span className="ml-auto tabular-nums font-normal normal-case tracking-normal text-muted-foreground/70">
                      {latencyMs >= 1000 ? `${(latencyMs / 1000).toFixed(1)}s` : `${latencyMs}ms`}
                    </span>
                  )}
                </button>

                {showMetadata && metadata && (
                  <div className="space-y-2.5 text-[11px]">
                    {/* Models */}
                    <div className="flex items-start gap-2">
                      <Brain size={11} className="text-purple-500 mt-0.5 shrink-0" />
                      <div className="space-y-0.5 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground">LLM:</span>
                          <span className="font-medium text-foreground/90">{metadata.llm_model}</span>
                          <span className="text-muted-foreground/60">({metadata.llm_provider})</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground">Embed:</span>
                          <span className="font-medium text-foreground/90">{metadata.embedding_model}</span>
                          <span className="text-muted-foreground/60">({metadata.embedding_provider}, {metadata.embedding_dim}d)</span>
                        </div>
                      </div>
                    </div>

                    {/* Graph stats */}
                    <div className="flex items-start gap-2">
                      <GitBranch size={11} className="text-emerald-500 mt-0.5 shrink-0" />
                      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                        <span>
                          <span className="text-muted-foreground">Seeds:</span>{" "}
                          <span className="font-medium tabular-nums">{metadata.seed_count}</span>
                          <span className="text-muted-foreground/60"> / top-{metadata.top_k}</span>
                        </span>
                        <span>
                          <span className="text-muted-foreground">Nodes:</span>{" "}
                          <span className="font-medium tabular-nums">{metadata.node_count}</span>
                        </span>
                        <span>
                          <span className="text-muted-foreground">Edges:</span>{" "}
                          <span className="font-medium tabular-nums">{metadata.edge_count}</span>
                        </span>
                        <span>
                          <span className="text-muted-foreground">Depth:</span>{" "}
                          <span className="font-medium tabular-nums">{metadata.traversal_depth}</span>
                        </span>
                      </div>
                    </div>

                    {/* Context */}
                    <div className="flex items-start gap-2">
                      <FileText size={11} className="text-blue-500 mt-0.5 shrink-0" />
                      <span>
                        <span className="text-muted-foreground">Context:</span>{" "}
                        <span className="font-medium tabular-nums">{metadata.context_length.toLocaleString()}</span>
                        <span className="text-muted-foreground/60"> chars</span>
                      </span>
                    </div>

                    {/* Step timings */}
                    {Object.keys(metadata.step_timings).length > 0 && (
                      <div className="flex items-start gap-2">
                        <Zap size={11} className="text-amber-500 mt-0.5 shrink-0" />
                        <div className="flex-1 space-y-1">
                          {Object.entries(metadata.step_timings).map(([step, ms]) => {
                            const totalMs = latencyMs || Object.values(metadata.step_timings).reduce((a, b) => a + b, 0);
                            const pct = totalMs > 0 ? (ms / totalMs) * 100 : 0;
                            return (
                              <div key={step} className="flex items-center gap-2">
                                <span className="text-muted-foreground w-24 shrink-0">{step.replace(/_/g, " ")}</span>
                                <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-primary/50"
                                    style={{ width: `${Math.min(pct, 100)}%` }}
                                  />
                                </div>
                                <span className="tabular-nums font-medium w-16 text-right shrink-0">
                                  {ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms.toFixed(0)}ms`}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      )}

      {/* Input row */}
      <div className="mt-auto relative">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit(question)}
          placeholder="Ask about ML papers, methods, datasets..."
          disabled={isLoading}
          className="w-full h-10 rounded-lg border border-border/60 bg-background pl-3.5 pr-11 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 disabled:opacity-50 transition-all duration-150"
        />
        <button
          onClick={() => handleSubmit(question)}
          disabled={isLoading || !question.trim()}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 h-7 w-7 rounded-md bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-30 disabled:pointer-events-none transition-all duration-150"
        >
          {isLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Send size={14} />
          )}
        </button>
      </div>
    </div>
  );
}
