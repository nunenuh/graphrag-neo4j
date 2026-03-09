import { FlaskConical } from "lucide-react";

export default function EvaluationPage() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <FlaskConical size={48} className="mx-auto text-muted-foreground/40" />
        <h2 className="text-lg font-semibold text-foreground">Evaluation Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Test pipeline accuracy, metrics, and baselines. Coming in Phase E.
        </p>
      </div>
    </div>
  );
}
