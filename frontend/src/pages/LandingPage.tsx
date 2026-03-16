import { Link } from "react-router-dom";
import { Network, Search, GitBranch, MessageSquare, ArrowRight, Database, Cpu, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-auto font-sans text-foreground">
      {/* Ambient background */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary/20 blur-[120px] opacity-60 dark:opacity-20" />
        <div className="absolute top-[20%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-emerald-500/20 blur-[120px] opacity-60 dark:opacity-20" />
        <div className="absolute bottom-[-20%] left-[20%] w-[60vw] h-[60vw] rounded-full bg-purple-500/20 blur-[150px] opacity-60 dark:opacity-20" />
      </div>

      <div className="relative z-10 flex flex-col">
        {/* Header */}
        <header className="border-b border-border/50 backdrop-blur-md bg-background/40">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20">
                <Network size={18} className="text-primary" />
              </div>
              <span className="text-sm font-semibold tracking-tight">graphrag-neo4j</span>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/dashboard"
                className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Open App
              </Link>
            </div>
          </div>
        </header>

        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 py-24 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-xs font-medium text-primary mb-6">
            <Zap size={12} />
            Powered by Knowledge Graphs + LLMs
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Graph RAG for{" "}
            <span className="text-primary">ML Research</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10">
            Ask natural language questions about machine learning papers, methods, tasks, and datasets.
            Get grounded answers backed by a knowledge graph with full provenance.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/query"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Try a Query <ArrowRight size={16} />
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-lg border border-border bg-card/50 hover:bg-accent/50 transition-colors"
            >
              View Dashboard
            </Link>
          </div>
        </section>

        {/* How it works */}
        <section className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <StepCard
              step={1}
              icon={Search}
              title="Ask a Question"
              description="Type a natural language question about ML research — methods, datasets, tasks, or papers."
            />
            <StepCard
              step={2}
              icon={GitBranch}
              title="Graph Search"
              description="Your question is embedded and matched to a knowledge graph via vector search + multi-hop traversal."
            />
            <StepCard
              step={3}
              icon={MessageSquare}
              title="Grounded Answer"
              description="An LLM generates an answer grounded in the retrieved subgraph, with provenance scoring."
            />
          </div>
        </section>

        {/* Tech stack */}
        <section className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-center mb-8">Tech Stack</h2>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <TechBadge icon={Database} label="Neo4j" />
            <TechBadge icon={Cpu} label="LangGraph" />
            <TechBadge icon={Network} label="React" />
            <TechBadge icon={Zap} label="FastAPI" />
            <TechBadge icon={Search} label="Vector + BM25" />
            <TechBadge icon={GitBranch} label="Multi-hop Traversal" />
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-border/50 backdrop-blur-md bg-background/40 mt-auto">
          <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between text-xs text-muted-foreground">
            <span>graphrag-neo4j &mdash; Graph RAG over ML Research Papers</span>
            <a
              href="https://github.com/nunenuh/graphrag-neo4j"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              GitHub
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}

function StepCard({
  step,
  icon: Icon,
  title,
  description,
}: {
  step: number;
  icon: typeof Search;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 text-center">
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-sm mb-4">
        {step}
      </div>
      <div className="flex justify-center mb-3">
        <Icon size={24} className="text-muted-foreground" />
      </div>
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function TechBadge({ icon: Icon, label }: { icon: typeof Database; label: string }) {
  return (
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm text-sm">
      <Icon size={14} className="text-muted-foreground" />
      {label}
    </div>
  );
}
