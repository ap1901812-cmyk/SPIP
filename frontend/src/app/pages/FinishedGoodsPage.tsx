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
  const [selectedBomExpansion, setSelectedBomExpansion] = useState<import("../../api/types").FGBOMExpansion | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "bom" | "inventory">("general");

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
      setActiveTab("general");
      const [detail, bomExp] = await Promise.all([
        finishedGoodsApi.getFinishedGood(id),
        finishedGoodsApi.getBOMExpansion(id).catch(() => null),
      ]);
      setSelectedFgDetail(detail);
      setSelectedBomExpansion(bomExp);
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
            Central workspace for Finished Goods master specs, BOM component trees, plant assignments, and inventory summaries.
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
                  <th>FG Base UOM</th>
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
          <div className="modal-content" style={{ maxWidth: "800px", width: "90%" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.25rem" }}>
                  {selectedFgDetail.code} – Workspace
                </h3>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                  {selectedFgDetail.description} | <strong>FG Base UOM:</strong> {selectedFgDetail.base_uom}
                </div>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem" }}
                onClick={() => setSelectedFgDetail(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", borderBottom: "1px solid var(--border-subtle)", marginBottom: "1rem", gap: "0.5rem" }}>
              <button
                type="button"
                className={`btn ${activeTab === "general" ? "btn-primary" : "btn-secondary"}`}
                style={{ borderRadius: "0.375rem 0.375rem 0 0", padding: "0.4rem 0.85rem", fontSize: "0.85rem" }}
                onClick={() => setActiveTab("general")}
              >
                General & Plants
              </button>
              <button
                type="button"
                className={`btn ${activeTab === "bom" ? "btn-primary" : "btn-secondary"}`}
                style={{ borderRadius: "0.375rem 0.375rem 0 0", padding: "0.4rem 0.85rem", fontSize: "0.85rem" }}
                onClick={() => setActiveTab("bom")}
              >
                BOM Components ({selectedFgDetail.rm_components_count + selectedFgDetail.pm_components_count})
              </button>
              <button
                type="button"
                className={`btn ${activeTab === "inventory" ? "btn-primary" : "btn-secondary"}`}
                style={{ borderRadius: "0.375rem 0.375rem 0 0", padding: "0.4rem 0.85rem", fontSize: "0.85rem" }}
                onClick={() => setActiveTab("inventory")}
              >
                Inventory Summary ({selectedFgDetail.inventory_snapshots.length})
              </button>
            </div>

            {activeTab === "general" && (() => {
              const rmCount = selectedFgDetail.rm_components_count;
              const activeRmCount = selectedBomExpansion?.rm_components ? selectedBomExpansion.rm_components.filter((c) => c.is_active).length : rmCount;
              const rmAvail = rmCount === 0 || activeRmCount === rmCount;

              const pmCount = selectedFgDetail.pm_components_count;
              const activePmCount = selectedBomExpansion?.pm_components ? selectedBomExpansion.pm_components.filter((c) => c.is_active).length : pmCount;
              const pmAvail = pmCount === 0 || activePmCount === pmCount;

              let overallStatus = "READY TO PRODUCE";
              let blockingItem: string | null = null;
              let blockingReason: string | null = null;

              if (!rmAvail && !pmAvail) {
                overallStatus = "PRODUCTION BLOCKED";
              } else if (!rmAvail) {
                overallStatus = "RM SHORTAGE";
                const b = selectedBomExpansion?.rm_components.find((c) => !c.is_active);
                if (b) {
                  blockingItem = b.component_material?.code || `MAT-#${b.component_material_id}`;
                  blockingReason = "Component Status Inactive / Insufficient Stock";
                }
              } else if (!pmAvail) {
                overallStatus = "PM SHORTAGE";
                const b = selectedBomExpansion?.pm_components.find((c) => !c.is_active);
                if (b) {
                  blockingItem = b.component_material?.code || `MAT-#${b.component_material_id}`;
                  blockingReason = "Component Status Inactive / Insufficient Stock";
                }
              }

              return (
                <div>
                  {/* Production Readiness Summary Card */}
                  <div
                    style={{
                      background: rmAvail && pmAvail ? "var(--status-healthy-bg)" : "var(--status-warning-bg)",
                      border: `1px solid ${rmAvail && pmAvail ? "var(--status-healthy-border)" : "var(--status-warning-border)"}`,
                      borderRadius: "0.5rem",
                      padding: "1.25rem",
                      marginBottom: "1.25rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                      <div>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
                          Production Readiness
                        </div>
                        <h4 style={{ margin: "0.25rem 0 0 0", fontSize: "1.1rem" }}>
                          Can this Finished Good currently be manufactured?
                        </h4>
                      </div>
                      <StatusBadge status={overallStatus} />
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                      <div style={{ background: "rgba(255,255,255,0.7)", padding: "0.75rem", borderRadius: "0.375rem" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>RM Availability</div>
                        <div style={{ fontSize: "1rem", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                          <span>{rmAvail ? "✓" : "✗"} {activeRmCount} / {rmCount} Available</span>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "0.15rem 0.45rem", fontSize: "0.7rem" }}
                            onClick={() => setActiveTab("bom")}
                          >
                            View Components
                          </button>
                        </div>
                      </div>

                      <div style={{ background: "rgba(255,255,255,0.7)", padding: "0.75rem", borderRadius: "0.375rem" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>PM Availability</div>
                        <div style={{ fontSize: "1rem", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                          <span>{pmAvail ? "✓" : "✗"} {activePmCount} / {pmCount} Available</span>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "0.15rem 0.45rem", fontSize: "0.7rem" }}
                            onClick={() => setActiveTab("bom")}
                          >
                            View Components
                          </button>
                        </div>
                      </div>
                    </div>

                    {blockingItem && (
                      <div style={{ marginTop: "1rem", padding: "0.6rem 0.75rem", background: "rgba(239, 68, 68, 0.1)", borderLeft: "3px solid var(--spip-red)", borderRadius: "0.25rem", fontSize: "0.85rem" }}>
                        <strong>Blocking Component:</strong> <span style={{ fontFamily: "monospace" }}>{blockingItem}</span> | <strong>Reason:</strong> {blockingReason}
                      </div>
                    )}
                  </div>

                  <div className="metrics-grid" style={{ marginBottom: "1rem" }}>
                    <KpiCard label="RM Components" value={selectedFgDetail.rm_components_count} />
                    <KpiCard label="PM Components" value={selectedFgDetail.pm_components_count} />
                    <KpiCard label="Assigned Plants" value={selectedFgDetail.plant_materials.length} />
                  </div>

                  <h4 style={{ margin: "1rem 0 0.5rem 0", fontSize: "0.95rem" }}>Plant Material Parameters</h4>
                  <div className="spip-table-container" style={{ marginBottom: "1rem" }}>
                    <table className="spip-table">
                      <thead>
                        <tr>
                          <th>Plant ID</th>
                          <th>Lead Time (Days)</th>
                          <th>Service Level (Z)</th>
                          <th>Safety Stock Override</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedFgDetail.plant_materials.map((pm) => (
                          <tr key={pm.id}>
                            <td>Plant #{pm.plant_id}</td>
                            <td>{pm.lead_time_days} days</td>
                            <td>{pm.service_level_z}</td>
                            <td>{pm.safety_stock_override !== undefined && pm.safety_stock_override !== null ? `${pm.safety_stock_override} ${selectedFgDetail.base_uom}` : "N/A"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })()}


            {activeTab === "bom" && (
              <div>
                <h4 style={{ margin: "0.5rem 0 0.5rem 0", fontSize: "0.95rem", color: "var(--spip-navy)" }}>
                  Raw Material (RM) Components
                </h4>
                <div className="spip-table-container" style={{ marginBottom: "1.25rem" }}>
                  <table className="spip-table">
                    <thead>
                      <tr>
                        <th>Component Code</th>
                        <th>Description</th>
                        <th>Required Qty</th>
                        <th>RM UOM</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedBomExpansion?.rm_components && selectedBomExpansion.rm_components.length > 0 ? (
                        selectedBomExpansion.rm_components.map((item) => (
                          <tr key={item.id}>
                            <td style={{ fontWeight: "600" }}>{item.component_material?.code || `MAT-#${item.component_material_id}`}</td>
                            <td>{item.component_material?.description || "Raw Material"}</td>
                            <td>{item.required_quantity}</td>
                            <td><strong>{item.unit_of_measure}</strong></td>
                            <td><StatusBadge status={item.is_active ? "ACTIVE" : "INACTIVE"} /></td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                            No Raw Material (RM) components mapped.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <h4 style={{ margin: "1rem 0 0.5rem 0", fontSize: "0.95rem", color: "var(--spip-navy)" }}>
                  Packaging Material (PM) Components
                </h4>
                <div className="spip-table-container" style={{ marginBottom: "1rem" }}>
                  <table className="spip-table">
                    <thead>
                      <tr>
                        <th>Component Code</th>
                        <th>Description</th>
                        <th>Required Qty</th>
                        <th>PM UOM</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedBomExpansion?.pm_components && selectedBomExpansion.pm_components.length > 0 ? (
                        selectedBomExpansion.pm_components.map((item) => (
                          <tr key={item.id}>
                            <td style={{ fontWeight: "600" }}>{item.component_material?.code || `MAT-#${item.component_material_id}`}</td>
                            <td>{item.component_material?.description || "Packaging Material"}</td>
                            <td>{item.required_quantity}</td>
                            <td><strong>{item.unit_of_measure}</strong></td>
                            <td><StatusBadge status={item.is_active ? "ACTIVE" : "INACTIVE"} /></td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                            No Packaging Material (PM) components mapped.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === "inventory" && (
              <div>
                <h4 style={{ margin: "0.5rem 0 0.5rem 0", fontSize: "0.95rem" }}>Inventory Snapshots</h4>
                <div className="spip-table-container" style={{ marginBottom: "1rem" }}>
                  <table className="spip-table">
                    <thead>
                      <tr>
                        <th>Snapshot Date</th>
                        <th>Plant ID</th>
                        <th>Usable Physical Stock</th>
                        <th>Reserved Stock</th>
                        <th>Blocked Stock</th>
                        <th>FG Base UOM</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedFgDetail.inventory_snapshots.length > 0 ? (
                        selectedFgDetail.inventory_snapshots.map((snap) => (
                          <tr key={snap.id}>
                            <td>{snap.snapshot_date}</td>
                            <td>{snap.plant_code || "Plant"}</td>
                            <td style={{ fontWeight: "700" }}>{snap.usable_physical_stock}</td>
                            <td>{snap.reserved_stock}</td>
                            <td>{snap.blocked_stock}</td>
                            <td>{snap.uom || selectedFgDetail.base_uom}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                            No inventory snapshots recorded.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div style={{ textAlign: "right", marginTop: "1rem" }}>
              <button type="button" className="btn btn-primary" onClick={() => setSelectedFgDetail(null)}>
                Close Workspace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

