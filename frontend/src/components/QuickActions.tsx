import { Link } from "react-router-dom";
import { MessageSquare, Globe, BarChart3, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";

const ACTIONS = [
  { to: "/query", label: "Ask a Question", icon: MessageSquare, description: "Query the knowledge graph with natural language" },
  { to: "/explore", label: "Explore Graph", icon: Globe, description: "Browse nodes and relationships" },
  { to: "/analytics", label: "View Analytics", icon: BarChart3, description: "Communities, trends, and centrality" },
  { to: "/evaluation", label: "Run Evaluation", icon: FlaskConical, description: "Test pipeline accuracy and metrics" },
] as const;

export function QuickActions() {
  return (
    <div className="grid grid-cols-4 gap-3">
      {ACTIONS.map(({ to, label, icon: Icon, description }) => (
        <Link key={to} to={to}>
          <Button
            variant="outline"
            className="w-full h-auto flex flex-col items-start gap-1 p-4 border-border/50"
          >
            <div className="flex items-center gap-2">
              <Icon size={14} className="text-primary" />
              <span className="text-sm font-medium">{label}</span>
            </div>
            <span className="text-[11px] text-muted-foreground text-left font-normal">
              {description}
            </span>
          </Button>
        </Link>
      ))}
    </div>
  );
}
