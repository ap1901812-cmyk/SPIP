import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { planningApi } from "../../api/services";
import type { PlanningCalculationResult } from "../../api/types";

export function PlanningDetailPage() {
  const { materialCode } = useParams<{ materialCode: string }>();
  const [searchParams] = useSearchParams();
  const plantCode = searchParams.get("plant_code") || "PLANT-1000";

  const [detail, setDetail] = useState<PlanningCalculationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!materialCode) return;
    setIsLoading(true);
    setError(null);
    planningApi
      .getMaterialPlanning(materialCode, plantCode)
      .then((res) => setDetail(res))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load material planning detail.")
      )
      .finally(() => setIsLoading(false));
  }, [materialCode, plantCode]);

  if (isLoading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        Loading material planning calculation components...
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div>
        <div className="alert alert-error">{error || "Material planning evaluation not found."}</div>
        <Link to="/" className="btn btn-secondary">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/" style={{ fontSize: "0.85rem", fontWeight: "600" }}>
            ← Back to Dashboard
          </Link>
          <h1 className="page-title" style={{ marginTop: "0.25rem" }}>
            {detail.material_code} — {detail.material_description}
          </h1>
          <div className="eyebrow" style={{ marginTop: "0.15rem" }}>
            PLANT: {detail.plant_code} ({detail.plant_name})
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <Link
            to={`/forecasting?material=${detail.material_code}&plant=${detail.plant_code}`}
            className="btn btn-secondary"
          >
            View Forecast
          </Link>
          <Link
            to={`/allocations?action=new&material=${detail.material_code}&plant=${detail.plant_code}`}
            className="btn btn-primary"
          >
            Create Allocation
          </Link>
        </div>
      </div>

      <div className="card" style={{ borderLeft: `6px solid var(--spip-red)` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div className="eyebrow">DETERMINISTIC CRITICALITY STATUS</div>
            <div style={{ marginTop: "0.35rem" }}>
              <span className={`badge-status ${detail.criticality_status}`} style={{ fontSize: "1rem" }}>
                {detail.criticality_status}
              </span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="eyebrow">AS-OF TIMESTAMP</div>
            <div style={{ fontSize: "0.85rem", fontWeight: "600", marginTop: "0.25rem" }}>
              {new Date(detail.as_of_timestamp).toLocaleString()}
            </div>
          </div>
        </div>

        <div style={{ marginTop: "1rem", padding: "0.75rem", background: "var(--surface-subtle)", borderRadius: "0.375rem" }}>
          <strong>Audit Explanation:</strong> {detail.explanation}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        <div className="card">
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--spip-red-dark)" }}>
            1. Demand Statistics & Lead Time
          </h4>
          <table className="spip-table">
            <tbody>
              <tr>
                <td>Average Daily Demand (D)</td>
                <td>
                  <strong>{detail.average_daily_demand} {detail.base_uom}/day</strong>
                </td>
              </tr>
              <tr>
                <td>Demand Std Dev (σ_d)</td>
                <td>{detail.demand_std_dev}</td>
              </tr>
              <tr>
                <td>Observation History Days</td>
                <td>{detail.observation_days_count} days</td>
              </tr>
              <tr>
                <td>Lead Time (LT)</td>
                <td>
                  <strong>{detail.lead_time_days} days</strong>
                </td>
              </tr>
              <tr>
                <td>Lead Time Source</td>
                <td><code>{detail.lead_time_source}</code></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--spip-red-dark)" }}>
            2. Safety Stock Policy (SS = Z × σ_d × √LT)
          </h4>
          <table className="spip-table">
            <tbody>
              <tr>
                <td>ABC Class</td>
                <td>
                  <span className="user-role-badge">Class {detail.abc_class}</span>
                </td>
              </tr>
              <tr>
                <td>Service Level Factor (Z)</td>
                <td>{detail.service_level_z}</td>
              </tr>
              <tr>
                <td>Calculated Safety Stock (SS)</td>
                <td>
                  <strong>{detail.safety_stock} {detail.base_uom}</strong>
                </td>
              </tr>
              <tr>
                <td>Manual SS Override</td>
                <td>{detail.is_safety_stock_overridden ? "Yes (Overridden)" : "No (Formula Active)"}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--spip-red-dark)" }}>
            3. Planning Availability (AI = Usable + PO - Committed)
          </h4>
          <table className="spip-table">
            <tbody>
              <tr>
                <td>Usable Physical Stock</td>
                <td>{detail.usable_physical_stock} {detail.base_uom}</td>
              </tr>
              <tr>
                <td>Reserved Stock (Excluded)</td>
                <td><small style={{ color: "var(--text-muted)" }}>{detail.reserved_stock_info} {detail.base_uom}</small></td>
              </tr>
              <tr>
                <td>Blocked Stock (Excluded)</td>
                <td><small style={{ color: "var(--text-muted)" }}>{detail.blocked_stock_info} {detail.base_uom}</small></td>
              </tr>
              <tr>
                <td>Eligible Incoming PO Qty</td>
                <td>+ {detail.eligible_incoming_po_qty} {detail.base_uom}</td>
              </tr>
              <tr>
                <td>Committed Allocations</td>
                <td>- {detail.committed_allocations} {detail.base_uom}</td>
              </tr>
              <tr style={{ background: "var(--surface-subtle)" }}>
                <td><strong>Planning Availability (AI)</strong></td>
                <td>
                  <strong style={{ color: "var(--spip-red-dark)", fontSize: "1rem" }}>
                    {detail.planning_availability} {detail.base_uom}
                  </strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--spip-red-dark)" }}>
            4. Reorder Point & Thresholds
          </h4>
          <table className="spip-table">
            <tbody>
              <tr>
                <td>Demand During Lead Time (D × LT)</td>
                <td>
                  <strong>{detail.demand_during_lead_time} {detail.base_uom}</strong>
                </td>
              </tr>
              <tr>
                <td>Reorder Point (ROP = D×LT + SS)</td>
                <td>
                  <strong style={{ color: "var(--spip-red)", fontSize: "1.1rem" }}>
                    {detail.reorder_point} {detail.base_uom}
                  </strong>
                </td>
              </tr>
              <tr>
                <td>Decision Horizon</td>
                <td>30 Days (Configurable)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
