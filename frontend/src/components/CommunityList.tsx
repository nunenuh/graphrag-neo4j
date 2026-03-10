import { useState } from "react";
import { ChevronDown, ChevronRight, Users } from "lucide-react";
import type { Community } from "@/types/api";

interface CommunityListProps {
  communities: Community[];
  totalCommunities: number;
}

export function CommunityList({ communities, totalCommunities }: CommunityListProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (communities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Users size={32} className="mb-2 opacity-40" />
        <p className="text-sm">No communities detected yet.</p>
        <p className="text-xs mt-1">Run analytics to detect communities.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {totalCommunities} communities detected
      </p>
      <div className="space-y-1.5">
        {communities.map((c) => {
          const isExpanded = expandedId === c.community_id;
          return (
            <div
              key={c.community_id}
              className="rounded-lg border border-border/50 bg-card overflow-hidden"
            >
              <button
                onClick={() => setExpandedId(isExpanded ? null : c.community_id)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-secondary/50 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown size={14} className="text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight size={14} className="text-muted-foreground shrink-0" />
                )}
                <span className="text-sm font-medium">Community {c.community_id}</span>
                <span className="ml-auto text-xs text-muted-foreground tabular-nums">
                  {c.member_count} members
                </span>
              </button>
              {isExpanded && c.top_members.length > 0 && (
                <div className="px-3 pb-2 pt-0">
                  <div className="border-t border-border/30 pt-2 space-y-1">
                    {c.top_members.map((m) => (
                      <div
                        key={m.uid}
                        className="flex items-center justify-between text-xs px-2 py-1 rounded bg-secondary/30"
                      >
                        <span className="text-foreground/80 truncate">{m.name}</span>
                        {m.pagerank !== undefined && (
                          <span className="text-muted-foreground tabular-nums shrink-0 ml-2">
                            PR: {m.pagerank.toFixed(4)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
