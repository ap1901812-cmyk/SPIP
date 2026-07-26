import { render, screen } from "@testing-library/react";
import { App } from "./App";

test("renders the foundation shell", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /foundation ready/i })).toBeInTheDocument();
  expect(screen.getByText("Skip to main content")).toHaveAttribute("href", "#main-content");
});
