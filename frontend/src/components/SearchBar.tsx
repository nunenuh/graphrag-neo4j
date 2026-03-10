import { useState, useEffect, useRef } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const LABEL_OPTIONS = ["All", "Paper", "Method", "Task", "Dataset"] as const;

interface SearchBarProps {
  onSearch: (query: string, label: string | undefined) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState<string>("All");
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (query.trim().length < 2) return;

    timerRef.current = setTimeout(() => {
      onSearch(query.trim(), label === "All" ? undefined : label);
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, label, onSearch]);

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search nodes by name..."
          className="pl-9 h-9 text-sm"
        />
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-9 text-xs min-w-[80px]">
            {label}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {LABEL_OPTIONS.map((opt) => (
            <DropdownMenuItem
              key={opt}
              onClick={() => setLabel(opt)}
              className="text-xs"
            >
              {opt}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
