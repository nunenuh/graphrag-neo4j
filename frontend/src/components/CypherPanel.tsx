import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, Terminal } from "lucide-react";

interface CypherPanelProps {
  cypher: string;
}

export function CypherPanel({ cypher }: CypherPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!cypher) return null;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground w-full px-1 py-1 rounded transition-colors font-medium uppercase tracking-wider">
        <Terminal size={11} />
        {isOpen ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        Cypher Query
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="text-xs bg-[hsl(224,50%,5%)] text-emerald-400 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap font-mono mt-1">
          {cypher}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
}
