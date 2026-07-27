import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { domainApi, planningApi } from "../../api/services";
import type { PlanningCalculationResult, Plant } from "../../api/types";

export function DashboardPage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<string>("PLANT-1000");
  const [summary, setSummary] = useState<PlanningCalculationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainApi
      .getPlants()
      .then((p) => setPlants(p))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    planningApi
      .getPlanningSummary(selectedPlant || undefined)
      .then((res) => setSummary(res))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load planning summary."))
      .finally(() => setIsLoading(false));
  }, [selectedPlant]);

  const criticalCount = summary.filter((s) => s.criticality_status === "CRITICAL").length;
  const warningCount = summary.filter((s) => s.criticality_status === "WARNING").length;
  const healthyCount = summary.filter((s) => s.criticality_status === "HEALTHY").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Inventory Planning Dashboard</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            REAL-TIME CRITICALITY & REORDER POINT MONITORING
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

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Materials</div>
          <div className="metric-value">{summary.length}</div>
        </div>

        <div className="metric-card critical">
          <div className="metric-label">Critical Items</div>
          <div className="metric-value" style={{ color: "var(--status-critical-text)" }}>
            {criticalCount}
          </div>
        </div>

        <div className="metric-card warning">
          <div className="metric-label">Warning Items</div>
          <div className="metric-value" style={{ color: "var(--status-warning-text)" }}>
            {warningCount}
          </div>
        </div>

        <div className="metric-card healthy">
          <div className="metric-label">Healthy Items</div>
          <div className="metric-value" style={{ color: "var(--status-healthy-text)" }}>
            {healthyCount}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Material Planning & Criticality Overview</h3>

        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            Evaluating material planning decision rules...
          </div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : summary.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            No planning data available for selected plant filter.
          </div>
        ) : (
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th>Plant</th>
                  <th>Material Code</th>
                  <th>Description</th>
                  <th>Usable Stock</th>
                  <th>Incoming PO</th>
                  <th>Planning Avail (AI)</th>
                  <th>Demand (D×LT)</th>
                  <th>Reorder Point (ROP)</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => (
                  <tr key={`${row.plant_code}-${row.material_code}`}>
                    <td>
                      <strong>{row.plant_code}</strong>
                    </td>
                    <td>
                      <Link to={`/planning/${row.material_code}?plant_code=${row.plant_code}`}>
                        <strong>{row.material_code}</strong>
                      </Link>
                    </td>
                    <td>{row.material_description}</td>
                    <td>
                      {row.usable_physical_stock.toLocaleString()} {row.base_uom}
                    </td>
                    <td>
                      {row.eligible_incoming_po_qty.toLocaleString()} {row.base_uom}
                    </td>
                    <td>
                      <strong>
                        {row.planning_availability.toLocaleString()} {row.base_uom}
                      </strong>
                    </td>
                    <td>
                      {row.demand_during_lead_time.toLocaleString()} {row.base_uom}
                    </td>
                    <td>
                      {row.reorder_point.toLocaleString()} {row.base_uom}
                    </td>
                    <td>
                      <span className={`badge-status ${row.criticality_status}`}>
                        {row.criticality_status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.35rem" }}>
                        <Link
                          to={`/planning/${row.material_code}?plant_code=${row.plant_code}`}
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                        >
                          Detail
                        </Link>
                        <Link
                          to={`/forecasting?material=${row.material_code}&plant=${row.plant_code}`}
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                        >
                          Forecast
                        </Link>
                        <Link
                          to={`/allocations?action=new&material=${row.material_code}&plant=${row.plant_code}`}
                          className="btn btn-primary"
                          style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                        >
                          Allocate
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
