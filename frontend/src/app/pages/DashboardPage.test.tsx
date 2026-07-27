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

  expect(await screen.findByRole("heading", { name: /Inventory Planning Dashboard/i })).toBeInTheDocument();
  expect(await screen.findByText(/Total Materials/i)).toBeInTheDocument();
  expect(await screen.findByText(/Critical Items/i)).toBeInTheDocument();
});
