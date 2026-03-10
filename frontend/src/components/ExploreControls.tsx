import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface ExploreControlsProps {
  limit: number;
  onLimitChange: (value: number) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function ExploreControls({
  limit,
  onLimitChange,
  onRefresh,
  isLoading,
}: ExploreControlsProps) {
  return (
    <div className="flex items-center gap-4 px-3 py-2 border-b border-border/50">
      <span className="text-xs text-muted-foreground shrink-0">
        Limit: {limit}
      </span>
      <Slider
        value={[limit]}
        onValueChange={([v]) => onLimitChange(v)}
        min={10}
        max={200}
        step={10}
        className="w-32"
      />
      <Button
        variant="ghost"
        size="sm"
        onClick={onRefresh}
        disabled={isLoading}
        className="h-7 px-2 text-xs gap-1.5"
      >
        <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
        Refresh
      </Button>
    </div>
  );
}
