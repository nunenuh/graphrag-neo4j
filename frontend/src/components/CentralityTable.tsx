import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowUpDown } from "lucide-react";
import type { CommunityMember } from "@/types/api";

interface CentralityTableProps {
  members: CommunityMember[];
}

type SortKey = "name" | "pagerank";

export function CentralityTable({ members }: CentralityTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("pagerank");
  const [sortAsc, setSortAsc] = useState(false);

  if (members.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p className="text-sm">No centrality data available.</p>
        <p className="text-xs mt-1">Run analytics to compute PageRank.</p>
      </div>
    );
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((v) => !v);
    } else {
      setSortKey(key);
      setSortAsc(key === "name");
    }
  };

  const sorted = [...members].sort((a, b) => {
    const dir = sortAsc ? 1 : -1;
    if (sortKey === "name") {
      return dir * a.name.localeCompare(b.name);
    }
    return dir * ((a.pagerank ?? 0) - (b.pagerank ?? 0));
  });

  return (
    <div className="rounded-lg border border-border/50 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-secondary/30">
            <TableHead className="w-12 text-center text-[11px]">#</TableHead>
            <TableHead>
              <button
                onClick={() => handleSort("name")}
                className="flex items-center gap-1 text-[11px] hover:text-foreground transition-colors"
              >
                Name
                <ArrowUpDown size={10} />
              </button>
            </TableHead>
            <TableHead className="text-right">
              <button
                onClick={() => handleSort("pagerank")}
                className="flex items-center gap-1 ml-auto text-[11px] hover:text-foreground transition-colors"
              >
                PageRank
                <ArrowUpDown size={10} />
              </button>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((m, i) => (
            <TableRow key={m.uid}>
              <TableCell className="text-center text-xs text-muted-foreground tabular-nums">
                {i + 1}
              </TableCell>
              <TableCell className="text-xs font-medium truncate max-w-[200px]">
                {m.name}
              </TableCell>
              <TableCell className="text-right text-xs tabular-nums text-muted-foreground">
                {m.pagerank !== undefined ? m.pagerank.toFixed(6) : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
