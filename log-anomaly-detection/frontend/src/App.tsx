import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "@/components/Layout/Sidebar";
import { DashboardPage } from "@/pages/DashboardPage";
import { AnomalyExplorerPage } from "@/pages/AnomalyExplorerPage";
import { AnomalyDetailPage } from "@/pages/AnomalyDetailPage";
import { LogExplorerPage } from "@/pages/LogExplorerPage";
import { ModelMonitoringPage } from "@/pages/ModelMonitoringPage";

export function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/anomalies" element={<AnomalyExplorerPage />} />
            <Route path="/anomalies/:id" element={<AnomalyDetailPage />} />
            <Route path="/logs" element={<LogExplorerPage />} />
            <Route path="/model" element={<ModelMonitoringPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
