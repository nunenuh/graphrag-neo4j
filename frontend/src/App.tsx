import { Routes, Route, Navigate } from "react-router-dom";
import { NavBar } from "@/components/NavBar";
import DashboardPage from "@/pages/DashboardPage";
import QueryPage from "@/pages/QueryPage";
import ExplorePage from "@/pages/ExplorePage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import EvaluationPage from "@/pages/EvaluationPage";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/query" element={<QueryPage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
