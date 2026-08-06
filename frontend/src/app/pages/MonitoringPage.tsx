import { useEffect, useState } from "react";
import { domainApi, monitoringApi } from "../../api/services";
import type { ExecutionHistoryItem, Plant, TelemetryMetrics } from "../../api/types";

export function MonitoringPage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<string>("");
  const [telemetry, setTelemetry] = useState<TelemetryMetrics | null>(null);
  const [executions, setExecutions] = useState<ExecutionHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    domainApi
      .getPlants()
      .then((p: Plant[]) => setPlants(p))
      .catch(() => {});

    loadTelemetry();
  }, [selectedPlant]);

  const loadTelemetry = () => {
    setIsLoading(true);

    Promise.all([
      monitoringApi.getTelemetry(selectedPlant || undefined),
      monitoringApi.getExecutions(selectedPlant || undefined, 50),
    ])
      .then(([tel, execs]: [TelemetryMetrics, ExecutionHistoryItem[]]) => {
        setTelemetry(tel);
        setExecutions(execs);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Planning Orchestrator Monitoring & Telemetry</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            REAL-TIME PIPELINE RUN LOGS, DURATION TRACKING & SYSTEM HEALTH
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label className="form-label" style={{ margin: 0 }}>
            Plant:
          </label>
          <select
            className="form-select"
            value={selectedPlant}
            onChange={(e) => setSelectedPlant(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="">All Plants</option>
            {plants.map((p) => (
              <option key={p.code} value={p.code}>
                {p.code} ({p.name})
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          Loading monitoring telemetry...
        </div>
      ) : (
        <>
          {/* Telemetry Metrics */}
          {telemetry ? (
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Total Executions</div>
                <div className="metric-value">{telemetry.total_executions}</div>
              </div>

              <div className="metric-card healthy">
                <div className="metric-label">Pipeline Success Rate</div>
                <div className="metric-value" style={{ color: "var(--status-healthy-text)" }}>
                  {telemetry.success_rate_percentage.toFixed(1)}%
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Avg Execution Duration</div>
                <div className="metric-value">{telemetry.average_duration_ms.toFixed(1)} ms</div>
              </div>

              <div className="metric-card critical">
                <div className="metric-label">Failed / Blocked Runs</div>
                <div className="metric-value" style={{ color: telemetry.failed_or_blocked_executions > 0 ? "var(--status-critical-text)" : "inherit" }}>
                  {telemetry.failed_or_blocked_executions}
                </div>
              </div>
            </div>
          ) : null}

          {/* Pipeline Executions Table */}
          <div className="card">
            <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Pipeline Execution History Log ({executions.length})</h3>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Execution ID</th>
                    <th>Plant</th>
                    <th>Material</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Executed Time</th>
                    <th>Failure Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map((ex) => (
                    <tr key={ex.id}>
                      <td><b>#{ex.id}</b></td>
                      <td>{ex.plant_code}</td>
                      <td>{ex.material_code || "ALL"}</td>
                      <td>
                        <span className={`badge ${ex.execution_status === "SUCCESS" ? "badge-success" : ex.execution_status === "BLOCKED" ? "badge-warning" : "badge-error"}`}>
                          {ex.execution_status}
                        </span>
                      </td>
                      <td>{ex.duration_ms?.toFixed(1)} ms</td>
                      <td>{ex.executed_at ? new Date(ex.executed_at).toLocaleString() : ""}</td>
                      <td><small>{ex.failure_reason || "None (Clean run)"}</small></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
