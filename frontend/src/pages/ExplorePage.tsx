import { Globe } from "lucide-react";

export default function ExplorePage() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Globe size={48} className="mx-auto text-muted-foreground/40" />
        <h2 className="text-lg font-semibold text-foreground">Graph Explorer</h2>
        <p className="text-sm text-muted-foreground">
          Browse and search the knowledge graph. Coming in Phase B.
        </p>
      </div>
    </div>
  );
}
