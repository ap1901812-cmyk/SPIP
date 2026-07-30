import { render, screen } from "@testing-library/react";
import { App } from "./App";

test("renders SPIP login screen by default when unauthenticated", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /^SPIP$/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^Sign In$/i })).toBeInTheDocument();
});
