import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/layouts/AppShell";
import { LoginPage, RegisterPage } from "@/features/auth/AuthPages";
import { DashboardPage } from "@/features/research/DashboardPage";
import { EvaluationPage } from "@/features/evaluation/EvaluationPage";
import { NewResearchPage } from "@/features/research/NewResearchPage";
import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { ResearchProgressPage } from "@/features/research/ResearchProgressPage";
import { ResearchResultsPage } from "@/features/research/ResearchResultsPage";
import { DocumentsPage } from "@/features/projects/DocumentsPage";
import { SavedReportsPage } from "@/features/reports/SavedReportsPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/research/new" element={<NewResearchPage />} />
          <Route path="/research/:id/progress" element={<ResearchProgressPage />} />
          <Route path="/research/:id" element={<ResearchResultsPage />} />
          <Route path="/saved-reports" element={<SavedReportsPage />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
