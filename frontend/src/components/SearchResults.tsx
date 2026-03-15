import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import type { SearchResult } from "@/types/api";

const BADGE_COLORS: Record<string, string> = {
  Paper: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  Method: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  Task: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  Dataset: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
  Author: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20",
  Repository: "bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20",
};

interface SearchResultsProps {
  results: SearchResult[];
  selectedUid: string | null;
  onSelect: (uid: string) => void;
}

export function SearchResults({ results, selectedUid, onSelect }: SearchResultsProps) {
  if (results.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-8">
        No results. Try a different search term.
      </p>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="space-y-1">
        {results.map((r) => {
          const desc =
            (r.properties.abstract as string) ||
            (r.properties.description as string) ||
            "";
          return (
            <button
              key={r.uid}
              onClick={() => onSelect(r.uid)}
              className={`w-full text-left p-2.5 rounded-lg transition-colors ${
                selectedUid === r.uid
                  ? "bg-accent"
                  : "hover:bg-accent/50"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${BADGE_COLORS[r.label] ?? ""}`}
                >
                  {r.label}
                </Badge>
                <span className="text-sm font-medium text-foreground truncate">
                  {r.name}
                </span>
              </div>
              {desc && (
                <p className="text-[11px] text-muted-foreground line-clamp-2">
                  {desc}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}
