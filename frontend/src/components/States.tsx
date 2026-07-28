import React from "react";

export const LoadingView: React.FC<{ message?: string }> = ({ message = "Loading data..." }) => (
  <div style={{ padding: "3rem 1.5rem", textAlign: "center", color: "var(--text-muted)" }}>
    <div style={{ fontSize: "1.2rem", fontWeight: "600", marginBottom: "0.5rem" }}>{message}</div>
    <div style={{ fontSize: "0.85rem" }}>Please wait while we fetch the latest planning information.</div>
  </div>
);

export const ErrorView: React.FC<{ message?: string; onRetry?: () => void }> = ({
  message = "Failed to load data.",
  onRetry,
}) => (
  <div className="alert alert-error" style={{ margin: "1.5rem 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    <div>
      <strong>Error:</strong> {message}
    </div>
    {onRetry && (
      <button type="button" className="btn btn-secondary" onClick={onRetry} style={{ padding: "0.25rem 0.75rem", fontSize: "0.8rem" }}>
        Retry
      </button>
    )}
  </div>
);

export const EmptyState: React.FC<{ title?: string; message?: string }> = ({
  title = "No Data Found",
  message = "There are no items matching the current filter criteria.",
}) => (
  <div className="card" style={{ padding: "3rem 1.5rem", textAlign: "center", color: "var(--text-muted)" }}>
    <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--text-main)" }}>{title}</h3>
    <p style={{ margin: 0, fontSize: "0.9rem" }}>{message}</p>
  </div>
);
