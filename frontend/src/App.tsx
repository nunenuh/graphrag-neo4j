import { Routes, Route, Navigate } from "react-router-dom";
import { NavBar } from "@/components/NavBar";
import DashboardPage from "@/pages/DashboardPage";
import QueryPage from "@/pages/QueryPage";
import ExplorePage from "@/pages/ExplorePage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import EvaluationPage from "@/pages/EvaluationPage";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-hidden font-sans text-foreground">
      {/* Dynamic Ambient Background to power the Glassmorphism */}
      <div className="fixed inset-0 z-0 pointer-events-none flex items-center justify-center overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary/20 blur-[120px] opacity-60 dark:opacity-20" />
        <div className="absolute top-[20%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-emerald-500/20 blur-[120px] opacity-60 dark:opacity-20" />
        <div className="absolute bottom-[-20%] left-[20%] w-[60vw] h-[60vw] rounded-full bg-purple-500/20 blur-[150px] opacity-60 dark:opacity-20" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        <NavBar />
        <main className="flex-1 flex flex-col min-h-0">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
