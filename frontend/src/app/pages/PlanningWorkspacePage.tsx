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

  const summary = planningResult?.summary || {};
  const criticalShortages = summary.critical_shortages_count || 0;
  const warningShortages = summary.warning_shortages_count || 0;
  const healthyShortages = (summary.total_components_evaluated || 0) - criticalShortages - warningShortages;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Planning Engine Workspace</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            FG Demand Explosion, Component Shortage Calculations, & Production Feasibility Analysis.
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={executePlanning}
          disabled={loading}
        >
          {loading ? "Calculating..." : "âš¡ Run Planning Engine"}
        </button>
      </div>

      <FilterBar
        searchTerm=""
        onSearchChange={() => {}}
        selectedPlant={selectedPlant}
        onPlantChange={handlePlantChange}
        plants={plants}
        placeholder="Filter planning calculations by plant..."
      />

      {loading ? (
        <LoadingView message="Executing FG Demand Explosion & Inventory Availability Calculations..." />
      ) : error ? (
        <ErrorView message={error} onRetry={executePlanning} />
      ) : !planningResult ? (
        <EmptyState title="No Planning Results" message="Click 'Run Planning Engine' to execute calculations." />
      ) : (
        <>
          <div className="metrics-grid">
            <KpiCard label="FG Demands Evaluated" value={summary.total_demand_items_evaluated || 0} subtitle="Forecast Items" />
            <KpiCard label="Component Requirements" value={summary.total_components_evaluated || 0} subtitle="BOM Components" />
            <KpiCard label="Critical Shortages" value={criticalShortages} type="critical" subtitle="Require PO Order" />
            <KpiCard label="Affected FGs" value={summary.affected_finished_goods_count || 0} type="warning" subtitle="Production Constraints" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
            <StatusDistributionChart
              criticalCount={criticalShortages}
              warningCount={warningShortages}
              healthyCount={healthyShortages > 0 ? healthyShortages : 0}
              title="Material Requirements Health Distribution"
            />
          </div>

          {/* Affected Finished Goods Table */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Production Impact Analysis (Finished Goods)
            </h3>
            {planningResult.affected_finished_goods.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No Finished Goods are constrained by component shortages.</div>
            ) : (
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>FG Code</th>
                      <th>Description</th>
                      <th>Forecast Demand</th>
                      <th>Feasible Production</th>
                      <th>Unmet Demand</th>
                      <th>Bottleneck Component</th>
                      <th>Status</th>
                      <th>Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planningResult.affected_finished_goods.map((fg, idx) => (
                      <tr key={idx}>
                        <td>{fg.plant_code}</td>
                        <td style={{ fontWeight: "700" }}>{fg.fg_code}</td>
                        <td>{fg.fg_description}</td>
                        <td style={{ fontWeight: "700" }}>{fg.forecast_demand}</td>
                        <td style={{ fontWeight: "700", color: "#16a34a" }}>{fg.feasible_production}</td>
                        <td style={{ fontWeight: "700", color: "var(--spip-red)" }}>{fg.unmet_demand}</td>
                        <td style={{ fontWeight: "600" }}>{fg.bottleneck_component_code || "None"}</td>
                        <td>
                          <StatusBadge status={fg.risk_status} />
                        </td>
                        <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: "250px" }}>{fg.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Component Requirements Table */}
          <div className="card">
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Component Gross & Net Requirements
            </h3>
            {planningResult.component_requirements.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No component requirements computed.</div>
            ) : (
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>Component Code</th>
                      <th>Description</th>
                      <th>Type</th>
                      <th>Gross Req</th>
                      <th>Physical Stock</th>
                      <th>Planning Availability</th>
                      <th>Shortage Qty</th>
                      <th>Status</th>
                      <th>Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planningResult.component_requirements.map((req, idx) => (
                      <tr key={idx}>
                        <td>{req.plant_code}</td>
                        <td style={{ fontWeight: "700" }}>{req.component_code}</td>
                        <td>{req.component_description}</td>
                        <td>
                          <StatusBadge status={req.component_type} />
                        </td>
                        <td style={{ fontWeight: "700" }}>{req.gross_requirement} {req.base_uom}</td>
                        <td>{req.usable_physical_stock} {req.base_uom}</td>
                        <td>{req.planning_availability} {req.base_uom}</td>
                        <td style={{ fontWeight: "700", color: req.shortage_quantity > 0 ? "var(--spip-red)" : "inherit" }}>
                          {req.shortage_quantity} {req.base_uom}
                        </td>
                        <td>
                          <StatusBadge status={req.criticality_status} />
                        </td>
                        <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: "250px" }}>{req.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
