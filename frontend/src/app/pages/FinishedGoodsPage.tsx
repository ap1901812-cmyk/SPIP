import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { domainApi, finishedGoodsApi } from "../../api/services";
import type { FinishedGoodDetail, FinishedGoodSummary, Plant } from "../../api/types";
import { FilterBar } from "../../components/FilterBar";
import { KpiCard } from "../../components/KpiCard";
import { EmptyState, ErrorView, LoadingView } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

export const FinishedGoodsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchFromUrl = searchParams.get("search") || "";
  const plantFromUrl = searchParams.get("plant") || "";

  const [searchTerm, setSearchTerm] = useState(searchFromUrl);
  const [selectedPlant, setSelectedPlant] = useState(plantFromUrl);
  const [fgList, setFgList] = useState<FinishedGoodSummary[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedFgDetail, setSelectedFgDetail] = useState<FinishedGoodDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [fgRes, plantRes] = await Promise.all([
        finishedGoodsApi.getFinishedGoods(),
        domainApi.getPlants(),
      ]);
      setFgList(fgRes);
      setPlants(plantRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load Finished Goods data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSearchChange = (val: string) => {
    setSearchTerm(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("search", val);
    else newParams.delete("search");
    setSearchParams(newParams);
  };

  const handlePlantChange = (val: string) => {
    setSelectedPlant(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("plant", val);
    else newParams.delete("plant");
    setSearchParams(newParams);
  };

  const handleOpenDetail = async (id: number) => {
    try {
      setDetailLoading(true);
      const detail = await finishedGoodsApi.getFinishedGood(id);
      setSelectedFgDetail(detail);
    } catch (err: any) {
      alert("Failed to load Finished Good detail.");
    } finally {
      setDetailLoading(false);
    }
  };

  const filtered = fgList.filter((fg) => {
    const matchesSearch =
      !searchTerm ||
      fg.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      fg.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const totalComponents = fgList.reduce((acc, curr) => acc + curr.component_count, 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Finished Goods Workspace</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Overview of Finished Goods, master specs, plant assignments, and BOM component counts.
          </div>
        </div>
      </div>

      <div className="metrics-grid">
        <KpiCard label="Finished Goods" value={fgList.length} type="healthy" subtitle="Active FG Master Records" />
        <KpiCard label="Manufacturing Plants" value={plants.length} subtitle="Plant Assignments" />
        <KpiCard label="Total BOM Mappings" value={totalComponents} subtitle="Derived Component Relations" />
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        selectedPlant={selectedPlant}
        onPlantChange={handlePlantChange}
        plants={plants}
        placeholder="Filter Finished Goods by code or description..."
      />

      {loading ? (
        <LoadingView message="Loading Finished Goods Workspace..." />
      ) : error ? (
        <ErrorView message={error} onRetry={fetchData} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No Finished Goods Found" message="Try broadening your search or plant filter." />
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th>FG Code</th>
                  <th>Description</th>
                  <th>Classification</th>
                  <th>Base UOM</th>
                  <th>Plants</th>
                  <th>BOM Components</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((fg) => (
                  <tr key={fg.id}>
                    <td style={{ fontWeight: "700" }}>{fg.code}</td>
                    <td>{fg.description}</td>
                    <td>
                      <StatusBadge status={fg.material_type} />
                    </td>
                    <td>{fg.base_uom}</td>
                    <td>{fg.plant_count} Plant(s)</td>
                    <td>{fg.component_count} Component(s)</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "0.25rem 0.65rem", fontSize: "0.8rem" }}
                        onClick={() => handleOpenDetail(fg.id)}
                        disabled={detailLoading}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedFgDetail && (
        <div className="modal-backdrop" onClick={() => setSelectedFgDetail(null)}>
          <div className="modal-content" style={{ maxWidth: "650px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem" }}>
                {selectedFgDetail.code} – Details
              </h3>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center" }}
                onClick={() => setSelectedFgDetail(null)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div style={{ fontSize: "0.9rem", marginBottom: "1rem" }}>
              <strong>Description:</strong> {selectedFgDetail.description} | <strong>Base UOM:</strong> {selectedFgDetail.base_uom}
            </div>

            <div className="metrics-grid" style={{ marginBottom: "1rem" }}>
              <KpiCard label="RM Components" value={selectedFgDetail.rm_components_count} />
              <KpiCard label="PM Components" value={selectedFgDetail.pm_components_count} />
              <KpiCard label="Stock Snapshots" value={selectedFgDetail.inventory_snapshots.length} />
            </div>

            <h4 style={{ margin: "1rem 0 0.5rem 0", fontSize: "0.95rem" }}>Plant Material Parameters</h4>
            <div className="spip-table-container" style={{ marginBottom: "1rem" }}>
              <table className="spip-table">
                <thead>
                  <tr>
                    <th>Plant ID</th>
                    <th>ABC Class</th>
                    <th>Safety Stock Override</th>
                    <th>Lead Time (Days)</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedFgDetail.plant_materials.map((pm) => (
                    <tr key={pm.id}>
                      <td>Plant #{pm.plant_id}</td>
                      <td>{pm.abc_class}</td>
                      <td>{pm.safety_stock_override ?? "N/A"}</td>
                      <td>{pm.lead_time_days} days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ textAlign: "right" }}>
              <button type="button" className="btn btn-primary" onClick={() => setSelectedFgDetail(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
