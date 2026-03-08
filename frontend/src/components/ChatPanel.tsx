import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2, Sparkles, Clock } from "lucide-react";
import type { SeedNode } from "@/types/api";

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
  isLoading: boolean;
  latencyMs?: number;
  exampleQuestions: string[];
}

export function ChatPanel({
  onSubmit,
  answer,
  seedNodes,
  isLoading,
  latencyMs,
  exampleQuestions,
}: ChatPanelProps) {
  const [question, setQuestion] = useState("");

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

      {/* Answer */}
      {answer && (
        <ScrollArea className="flex-1 rounded-lg border border-border/40 bg-secondary/30">
          <div className="p-4 space-y-3">
            <p className="text-[13px] leading-relaxed whitespace-pre-wrap text-foreground/90">
              {answer}
            </p>
            {latencyMs !== undefined && (
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground/70">
                <Clock size={10} />
                <span className="tabular-nums">{latencyMs}ms</span>
              </div>
            )}
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
