import { useEffect, useState } from "react";
import { decisionSupportApi } from "../api/services";
import type { ExplainabilityReportDTO } from "../api/types";

interface Props {
  plantCode: string;
  materialCode: string;
  isOpen: boolean;
  onClose: () => void;
}

export function ExplainabilityDrawer({ plantCode, materialCode, isOpen, onClose }: Props) {
  const [report, setReport] = useState<ExplainabilityReportDTO | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && plantCode && materialCode) {
      setIsLoading(true);
      setError(null);
      decisionSupportApi
        .getExplainability(plantCode, materialCode)
        .then((data: ExplainabilityReportDTO) => setReport(data))
        .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load explainability."))
        .finally(() => setIsLoading(false));
    }
  }, [isOpen, plantCode, materialCode]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "550px",
        backgroundColor: "var(--bg-card, #1E1E2E)",
        boxShadow: "-4px 0 20px rgba(0,0,0,0.5)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        padding: "1.5rem",
        overflowY: "auto",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <span className="badge badge-info">💡 Decision Rationale</span>
          <h2 style={{ margin: "0.25rem 0 0 0" }}>Why? - Decision Breakdown</h2>
        </div>
        <button onClick={onClose} className="btn btn-secondary" style={{ padding: "0.25rem 0.5rem" }}>
          ✕ Close
        </button>
      </div>

      {isLoading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          Building explainability decision breakdown...
        </div>
      ) : error ? (
        <div className="alert alert-error">{error}</div>
      ) : report ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Header context */}
          <div className="card" style={{ padding: "1rem" }}>
            <div><b>Plant:</b> {report.plant_code}</div>
            <div><b>Material:</b> {report.material_code} - {report.material_description}</div>
            <div><b>Type:</b> {report.material_type}</div>
          </div>

          {/* Final Recommendation */}
          <div className="card" style={{ borderLeft: "4px solid var(--accent-primary)", padding: "1rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0" }}>Final Decision & Action</h4>
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <span className="badge badge-error">{report.final_recommendation.priority}</span>
              <span className="badge badge-info">{report.final_recommendation.suggested_procurement_action}</span>
            </div>
            <p style={{ margin: 0, fontSize: "0.9rem" }}>{report.final_recommendation.reason}</p>
          </div>

          {/* Intermediate Math */}
          <div className="card" style={{ padding: "1rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0" }}>Intermediate Calculations</h4>
            <table className="data-table" style={{ fontSize: "0.85rem" }}>
              <tbody>
                <tr><td>Average Daily Demand ($D_{'{avg}'}$)</td><td>{report.intermediate_calculations.average_daily_demand} KG/day</td></tr>
                <tr><td>Usable Stock</td><td>{report.intermediate_calculations.usable_physical_stock} KG</td></tr>
                <tr><td>Planning Available Stock</td><td><b>{report.intermediate_calculations.planning_available_inventory} KG</b></td></tr>
                <tr><td>Trigger 1 Level</td><td>{report.intermediate_calculations.trigger_1} KG</td></tr>
                <tr><td>Trigger 2 Level</td><td>{report.intermediate_calculations.trigger_2} KG</td></tr>
              </tbody>
            </table>
          </div>

          {/* Business Rules Applied */}
          <div className="card" style={{ padding: "1rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0" }}>Business Rules Applied</h4>
            <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.85rem" }}>
              {report.business_rules_applied.map((rule, i) => (
                <li key={i} style={{ marginBottom: "0.25rem" }}>{rule}</li>
              ))}
            </ul>
          </div>

          {/* Source Data Used */}
          <div className="card" style={{ padding: "1rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0" }}>Source Data Used</h4>
            <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.85rem" }}>
              {report.source_data_used.map((src, i) => (
                <li key={i} style={{ marginBottom: "0.25rem" }}>
                  <b>{src.entity}</b> ({src.source}): {src.description}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}
