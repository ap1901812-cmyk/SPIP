import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { domainApi, fgPlanningApi } from "../../api/services";
import type { FGPlanningResult, Plant } from "../../api/types";
import { FilterBar } from "../../components/FilterBar";
import { KpiCard } from "../../components/KpiCard";
import { StatusDistributionChart } from "../../components/PlanningCharts";
import { EmptyState, ErrorView, LoadingView } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

export const PlanningWorkspacePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const plantFromUrl = searchParams.get("plant") || "";

  const [selectedPlant, setSelectedPlant] = useState(plantFromUrl);
  const [materialTypeFilter, setMaterialTypeFilter] = useState<"ALL" | "RM" | "PM">("ALL");
  const [plants, setPlants] = useState<Plant[]>([]);
  const [planningResult, setPlanningResult] = useState<FGPlanningResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlants = async () => {
    try {
      const res = await domainApi.getPlants();
      setPlants(res);
    } catch (err) {
      console.error(err);
    }
  };

  const executePlanning = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fgPlanningApi.runPlanning({
        plant_code: selectedPlant || undefined,
      });
      setPlanningResult(res);
    } catch (err: any) {
      setError(err?.message || "Failed to execute planning calculations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlants();
    executePlanning();
  }, []);

  const handlePlantChange = (val: string) => {
    setSelectedPlant(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("plant", val);
    else newParams.delete("plant");
    setSearchParams(newParams);
  };

  const summary: Record<string, any> = planningResult?.summary || {};
  const criticalShortages = Number(summary.critical_shortages_count || 0);
  const warningShortages = Number(summary.warning_shortages_count || 0);
  const healthyShortages = Number(summary.total_components_evaluated || 0) - criticalShortages - warningShortages;

  // Filter component requirements: Exclude FG (Finished Goods), and filter by ALL / RM / PM
  const filteredComponents = (planningResult?.component_requirements || []).filter((req) => {
    const typeUpper = (req.component_type || "").toUpperCase();
    if (typeUpper === "FINISHED_GOODS" || typeUpper === "FG") return false;
    if (materialTypeFilter === "RM") {
      return typeUpper === "RAW_MATERIAL" || typeUpper === "RM";
    }
    if (materialTypeFilter === "PM") {
      return typeUpper === "PACKAGING" || typeUpper === "PM";
    }
    return true; // ALL = RM + PM
  });

  const [selectedExplanation, setSelectedExplanation] = useState<{ code: string; text: string } | null>(null);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Planning Overview Workspace</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Component Demand Explosion, Inventory Availability, Shortage Analysis & Replenishment.
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={executePlanning}
          disabled={loading}
        >
          {loading ? (
            "Calculating..."
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: "0.4rem" }}>
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              Run Planning Engine
            </>
          )}
        </button>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <div style={{ flex: 1, minWidth: "260px" }}>
          <FilterBar
            searchTerm=""
            onSearchChange={() => {}}
            selectedPlant={selectedPlant}
            onPlantChange={handlePlantChange}
            plants={plants}
            placeholder="Filter planning calculations by plant..."
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", background: "var(--surface-card)", padding: "0.25rem 0.5rem", borderRadius: "0.5rem", border: "1px solid var(--border-subtle)" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)", marginRight: "0.25rem" }}>Material Type:</span>
          <button
            type="button"
            className={`btn ${materialTypeFilter === "ALL" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "0.25rem 0.65rem", fontSize: "0.8rem" }}
            onClick={() => setMaterialTypeFilter("ALL")}
          >
            All
          </button>
          <button
            type="button"
            className={`btn ${materialTypeFilter === "RM" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "0.25rem 0.65rem", fontSize: "0.8rem" }}
            onClick={() => setMaterialTypeFilter("RM")}
          >
            RM
          </button>
          <button
            type="button"
            className={`btn ${materialTypeFilter === "PM" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "0.25rem 0.65rem", fontSize: "0.8rem" }}
            onClick={() => setMaterialTypeFilter("PM")}
          >
            PM
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingView message="Executing Component Demand Explosion & Availability Calculations..." />
      ) : error ? (
        <ErrorView message={error} onRetry={executePlanning} />
      ) : !planningResult ? (
        <EmptyState title="No Planning Results" message="Click 'Run Planning Engine' to execute calculations." />
      ) : (
        <>
          <div className="metrics-grid">
            <KpiCard label="FG Demands Evaluated" value={summary.total_demand_items_evaluated || 0} subtitle="Forecast Items" />
            <KpiCard label="Component Requirements" value={filteredComponents.length} subtitle="RM & PM Components" />
            <KpiCard label="Critical Shortages" value={criticalShortages} type="critical" subtitle="Require PO Order" />
            <KpiCard label="Warning Shortages" value={warningShortages} type="warning" subtitle="Reorder Point Threshold" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
            <StatusDistributionChart
              criticalCount={criticalShortages}
              warningCount={warningShortages}
              healthyCount={healthyShortages > 0 ? healthyShortages : 0}
              title="Material Requirements Health Distribution"
            />
          </div>

          {/* Component Requirements Table */}
          <div className="card">
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Component Gross & Net Requirements ({materialTypeFilter})
            </h3>
            {filteredComponents.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No component requirements match the selected filter.</div>
            ) : (
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>Component Code</th>
                      <th>Description</th>
                      <th>Material Type</th>
                      <th>Gross Req</th>
                      <th>Physical Stock</th>
                      <th>Planning Availability</th>
                      <th>Shortage Qty</th>
                      <th>Component UOM</th>
                      <th>Material Inventory Status</th>
                      <th style={{ textAlign: "right" }}>Audit Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredComponents.map((req, idx) => (
                      <tr key={idx}>
                        <td>{req.plant_code}</td>
                        <td style={{ fontWeight: "700" }}>{req.component_code}</td>
                        <td>{req.component_description}</td>
                        <td>
                          <StatusBadge status={req.component_type} />
                        </td>
                        <td style={{ fontWeight: "700" }}>{req.gross_requirement}</td>
                        <td>{req.usable_physical_stock}</td>
                        <td>{req.planning_availability}</td>
                        <td style={{ fontWeight: "700", color: req.shortage_quantity > 0 ? "var(--spip-red)" : "inherit" }}>
                          {req.shortage_quantity}
                        </td>
                        <td><strong>{req.base_uom}</strong></td>
                        <td>
                          <StatusBadge status={req.criticality_status} />
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                            onClick={() => setSelectedExplanation({ code: req.component_code, text: req.explanation })}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {selectedExplanation && (
        <div className="modal-backdrop" onClick={() => setSelectedExplanation(null)}>
          <div className="modal-content" style={{ maxWidth: "540px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.1rem" }}>
                Audit Explanation – {selectedExplanation.code}
              </h3>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem" }}
                onClick={() => setSelectedExplanation(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ background: "var(--surface-subtle)", padding: "1rem", borderRadius: "0.5rem", marginBottom: "1.25rem", fontSize: "0.9rem", lineHeight: 1.5 }}>
              {selectedExplanation.text}
            </div>

            <div style={{ textAlign: "right" }}>
              <button type="button" className="btn btn-primary" onClick={() => setSelectedExplanation(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


