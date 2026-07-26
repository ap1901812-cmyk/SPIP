import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return <main className="app-shell"><a className="skip-link" href="#main-content">Skip to main content</a><header className="app-header"><span className="brand-mark" aria-hidden="true">SP</span><div><h1>Supply Planning Intelligence Platform</h1><p>Engineering foundation</p></div></header><section id="main-content" tabIndex={-1}>{children}</section></main>;
}
