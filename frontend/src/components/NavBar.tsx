import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  Globe,
  BarChart3,
  FlaskConical,
  Network,
} from "lucide-react";
import { StatusBadges } from "@/components/StatusBadges";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/query", label: "Query", icon: MessageSquare },
  { to: "/explore", label: "Explore", icon: Globe },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/evaluation", label: "Evaluation", icon: FlaskConical },
] as const;

export function NavBar() {
  return (
    <header className="relative z-10 border-b border-border/50 backdrop-blur-md bg-background/40">
      <div className="px-6 py-3 flex items-center gap-6">
        {/* Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20">
            <Network size={18} className="text-primary" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              graphrag-neo4j
            </h1>
            <p className="text-[11px] text-muted-foreground leading-none">
              Graph RAG over ML Research Papers
            </p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${isActive
                  ? "text-foreground bg-accent"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`
              }
            >
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-2">
          <StatusBadges />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
