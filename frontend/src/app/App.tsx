import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "./useAuth";


import { AppShell } from "./AppShell";
import { AllocationsPage } from "./pages/AllocationsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForecastingPage } from "./pages/ForecastingPage";
import { IngestionPage } from "./pages/IngestionPage";
import { LoginPage } from "./pages/LoginPage";
import { ManagerApprovalPage } from "./pages/ManagerApprovalPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PlanningDetailPage } from "./pages/PlanningDetailPage";
import { ReportsPage } from "./pages/ReportsPage";

import { queryClient } from "./query-client";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
        Loading SPIP Session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="planning" element={<DashboardPage />} />
              <Route path="planning/:materialCode" element={<PlanningDetailPage />} />
              <Route path="forecasting" element={<ForecastingPage />} />
              <Route path="allocations" element={<AllocationsPage />} />
              <Route path="approvals" element={<ManagerApprovalPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="ingestion" element={<IngestionPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}



export default App;
