import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { domainApi, fgPlanningApi } from "../../api/services";
import type { Plant, ProcurementRecommendation, RecommendationSummary, ShortageSummary } from "../../api/types";
import { FilterBar } from "../../components/FilterBar";
import { KpiCard } from "../../components/KpiCard";
import { EmptyState, ErrorView, LoadingView } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

export const PlanningInsightsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const plantFromUrl = searchParams.get("plant") || "";

  const [selectedPlant, setSelectedPlant] = useState(plantFromUrl);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [shortageData, setShortageData] = useState<ShortageSummary | null>(null);
  const [recommendationData, setRecommendationData] = useState<RecommendationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      setError(null);
      const [plantRes, shortageRes, recRes] = await Promise.all([
        domainApi.getPlants(),
        fgPlanningApi.getShortages(selectedPlant || undefined),
        fgPlanningApi.getRecommendations(selectedPlant || undefined),
      ]);
      setPlants(plantRes);
      setShortageData(shortageRes);
      setRecommendationData(recRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load material shortage insights.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [selectedPlant]);

  const handlePlantChange = (val: string) => {
    setSelectedPlant(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("plant", val);
    else newParams.delete("plant");
    setSearchParams(newParams);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Shortages & Procurement Recommendations</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Identify material supply shortages and view explainable procurement recommendations.
          </div>
        </div>
      </div>

      <FilterBar
        searchTerm=""
        onSearchChange={() => {}}
        selectedPlant={selectedPlant}
        onPlantChange={handlePlantChange}
        plants={plants}
        placeholder="Filter insights by plant..."
      />

      {loading ? (
        <LoadingView message="Loading Shortage & Procurement Recommendations..." />
      ) : error ? (
        <ErrorView message={error} onRetry={fetchInsights} />
      ) : (
        <>
          <div className="metrics-grid">
            <KpiCard label="Total Material Shortages" value={shortageData?.total_shortages_count || 0} type="warning" />
            <KpiCard label="Critical Shortages" value={shortageData?.critical_shortages_count || 0} type="critical" />
            <KpiCard label="Procurement Orders Recommended" value={recommendationData?.total_recommendations_count || 0} type="healthy" />
          </div>

          {/* Material Shortages Table */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Material Shortages
            </h3>
            {!shortageData || shortageData.shortages.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No material shortages detected. All required materials have sufficient planning availability.</div>
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
                      <th>Availability</th>
                      <th>Shortage Qty</th>
                      <th>Status</th>
                      <th>Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shortageData.shortages.map((s, idx) => (
                      <tr key={idx}>
                        <td>{s.plant_code}</td>
                        <td style={{ fontWeight: "700" }}>{s.component_code}</td>
                        <td>{s.component_description}</td>
                        <td>
                          <StatusBadge status={s.component_type} />
                        </td>
                        <td>{s.gross_requirement} {s.base_uom}</td>
                        <td>{s.planning_availability} {s.base_uom}</td>
                        <td style={{ fontWeight: "700", color: "var(--spip-red)" }}>{s.shortage_quantity} {s.base_uom}</td>
                        <td>
                          <StatusBadge status={s.criticality_status} />
                        </td>
                        <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: "250px" }}>{s.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Procurement Recommendations Table */}
          <div className="card">
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Procurement Recommendations
            </h3>
            {!recommendationData || recommendationData.recommendations.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No procurement recommendations required.</div>
            ) : (
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>Component Code</th>
                      <th>Shortage Qty</th>
                      <th>Recommended Order Qty</th>
                      <th>Primary Vendor</th>
                      <th>Lead Time</th>
                      <th>Min Order Qty (MOQ)</th>
                      <th>Procurement Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recommendationData.recommendations.map((rec, idx) => (
                      <tr key={idx}>
                        <td>{rec.plant_code}</td>
                        <td style={{ fontWeight: "700" }}>{rec.component_code}</td>
                        <td style={{ color: "var(--spip-red)", fontWeight: "700" }}>{rec.shortage_quantity} {rec.uom}</td>
                        <td style={{ color: "#16a34a", fontWeight: "700" }}>{rec.recommended_order_qty} {rec.uom}</td>
                        <td>{rec.vendor_name || rec.vendor_code || "Primary Vendor"}</td>
                        <td>{rec.lead_time_days} days</td>
                        <td>{rec.min_order_qty > 0 ? `${rec.min_order_qty} ${rec.uom}` : "None"}</td>
                        <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: "250px" }}>{rec.explanation}</td>
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
