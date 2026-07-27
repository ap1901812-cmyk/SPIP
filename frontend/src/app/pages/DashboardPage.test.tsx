import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../AuthContext";
import { queryClient } from "../query-client";
import { DashboardPage } from "./DashboardPage";

test("renders dashboard heading and metrics grid", async () => {
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );

  expect(screen.getByRole("heading", { name: /Inventory Planning Dashboard/i })).toBeInTheDocument();
  expect(screen.getByText(/Total Materials/i)).toBeInTheDocument();
  expect(screen.getByText(/Critical Items/i)).toBeInTheDocument();
});
