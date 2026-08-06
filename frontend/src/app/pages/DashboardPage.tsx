import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { decisionSupportApi, domainApi } from "../../api/services";
import type { DecisionSupportSummaryDTO, Plant } from "../../api/types";
import { EmptyState } from "../../components/States";

export function DashboardPage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<string>("");
  const [dsData, setDsData] = useState<DecisionSupportSummaryDTO | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainApi
      .getPlants()
      .then((p: Plant[]) => {
        setPlants(p);
        if (p.length > 0) {
          setSelectedPlant(p[0].code);
        } else {
          setIsLoading(false);
        }
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedPlant) return;
    setIsLoading(true);
    setError(null);

    decisionSupportApi
      .getSummary(selectedPlant)
      .then((res: DecisionSupportSummaryDTO) => setDsData(res))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load decision summary."))
      .finally(() => setIsLoading(false));
  }, [selectedPlant]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">SPIP V2 Enterprise Planning Dashboard</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            INTELLIGENCE, READINESS & PROCUREMENT ORCHESTRATION
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
          Loading Enterprise Intelligence Dashboard...
        </div>
      ) : error ? (
        <div className="alert alert-error">{error}</div>
      ) : dsData ? (
        <>
          {/* Executive Overview Cards */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Planning Readiness</div>
              <div
                className="metric-value"
                style={{
                  color:
                    dsData.planning_summary.readiness_state === "READY"
                      ? "var(--status-healthy-text)"
                      : "var(--status-warning-text)",
                }}
              >
                {dsData.planning_summary.readiness_score.toFixed(1)}%
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                State: {dsData.planning_summary.readiness_state}
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Available Inventory</div>
              <div className="metric-value">
                {dsData.inventory_summary.planning_available_inventory.toLocaleString()} KG
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                Days of Inventory (DOI): {dsData.inventory_summary.days_of_inventory.toFixed(1)} days
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Production Readiness</div>
              <div className="metric-value" style={{ color: "var(--status-healthy-text)" }}>
                {dsData.production_summary.production_readiness_percentage.toFixed(1)}%
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                {dsData.production_summary.ready_to_produce_fg_count} Ready / {dsData.production_summary.blocked_fg_count} Blocked
              </div>
            </div>

            <div className="metric-card critical">
              <div className="metric-label">Critical Shortages</div>
              <div className="metric-value" style={{ color: "var(--status-critical-text)" }}>
                {dsData.procurement_summary.critical_priority_count}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                {dsData.procurement_summary.total_recommendations_count} Total Recs
              </div>
            </div>
          </div>

          {/* Module Intelligence Breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            {/* Inventory & Consumption Widget */}
            <div className="card">
              <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Inventory & Consumption Intelligence</h3>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td><b>Usable Physical Stock</b></td>
                    <td>{dsData.inventory_summary.usable_physical_stock.toLocaleString()} KG</td>
                  </tr>
                  <tr>
                    <td><b>Incoming PO Quantity</b></td>
                    <td>{dsData.inventory_summary.incoming_po_quantity.toLocaleString()} KG</td>
                  </tr>
                  <tr>
                    <td><b>Planning Available Stock</b></td>
                    <td><b>{dsData.inventory_summary.planning_available_inventory.toLocaleString()} KG</b></td>
                  </tr>
                  <tr>
                    <td><b>Average Daily Demand</b></td>
                    <td>{dsData.inventory_summary.average_daily_demand.toLocaleString()} KG/day</td>
                  </tr>
                  <tr>
                    <td><b>Days of Inventory (DOI)</b></td>
                    <td><span className="badge badge-info">{dsData.inventory_summary.days_of_inventory.toFixed(1)} days</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Procurement & Allocation Widget */}
            <div className="card">
              <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Procurement & Allocations</h3>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td><b>Total Procurement Recommendations</b></td>
                    <td>{dsData.procurement_summary.total_recommendations_count}</td>
                  </tr>
                  <tr>
                    <td><b>Critical Priority Items</b></td>
                    <td><span className="badge badge-error">{dsData.procurement_summary.critical_priority_count}</span></td>
                  </tr>
                  <tr>
                    <td><b>High Priority Items</b></td>
                    <td><span className="badge badge-warning">{dsData.procurement_summary.high_priority_count}</span></td>
                  </tr>
                  <tr>
                    <td><b>Total Allocated Quantity</b></td>
                    <td><b>{dsData.procurement_summary.total_allocated_quantity.toLocaleString()} KG</b></td>
                  </tr>
                </tbody>
              </table>
              <div style={{ marginTop: "1rem", textAlign: "right" }}>
                <Link to="/allocations" className="btn btn-secondary" style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}>
                  Manage Allocations →
                </Link>
              </div>
            </div>
          </div>

          {/* Actionable Recommendations Table */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0 }}>Actionable Procurement Recommendations</h3>
              <Link to="/reports" className="btn btn-secondary" style={{ fontSize: "0.85rem" }}>
                View Full Reports
              </Link>
            </div>

            {dsData.recommendation_summary.length === 0 ? (
              <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)" }}>
                No active procurement recommendations for this plant. Inventory is healthy.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Material Code</th>
                    <th>Recommended Qty</th>
                    <th>Priority</th>
                    <th>Planning Mode</th>
                    <th>Status</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {dsData.recommendation_summary.map((rec) => (
                    <tr key={rec.id}>
                      <td><b>{rec.material_code}</b></td>
                      <td>{rec.recommended_qty.toLocaleString()} KG</td>
                      <td>
                        <span className={`badge ${rec.priority === "CRITICAL" ? "badge-error" : rec.priority === "HIGH" ? "badge-warning" : "badge-info"}`}>
                          {rec.priority}
                        </span>
                      </td>
                      <td>{rec.planning_mode}</td>
                      <td><span className="badge badge-success">{rec.status}</span></td>
                      <td><small>{rec.reason}</small></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : (
        <EmptyState
          title="No Planning Data Available"
          message="No plant or planning data available. Please upload or import master data to start planning."
        />
      )}
    </div>
  );
}
