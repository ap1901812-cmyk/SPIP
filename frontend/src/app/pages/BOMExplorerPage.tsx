import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { bomApi } from "../../api/services";
import type { BOMItem, FGBOMExpansion } from "../../api/types";
import { FilterBar } from "../../components/FilterBar";
import { KpiCard } from "../../components/KpiCard";
import { EmptyState, ErrorView, LoadingView } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

export const BOMExplorerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchFromUrl = searchParams.get("search") || "";

  const [searchTerm, setSearchTerm] = useState(searchFromUrl);
  const [boms, setBoms] = useState<BOMItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expansionData, setExpansionData] = useState<FGBOMExpansion | null>(null);
  const [expansionLoading, setExpansionLoading] = useState(false);

  const fetchBOMs = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await bomApi.getBOMs();
      setBoms(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load Bill of Materials.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBOMs();
  }, []);

  const handleSearchChange = (val: string) => {
    setSearchTerm(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("search", val);
    else newParams.delete("search");
    setSearchParams(newParams);
  };

  const handleExpandBOM = async (fgId: number) => {
    try {
      setExpansionLoading(true);
      const exp = await bomApi.getExpansion(fgId);
      setExpansionData(exp);
    } catch (err: any) {
      alert("Failed to load expanded BOM components.");
    } finally {
      setExpansionLoading(false);
    }
  };

  const filtered = boms.filter((b) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    const fgCode = b.fg_material?.code?.toLowerCase() || "";
    const compCode = b.component_material?.code?.toLowerCase() || "";
    const compDesc = b.component_material?.description?.toLowerCase() || "";
    return fgCode.includes(term) || compCode.includes(term) || compDesc.includes(term);
  });

  const activeCount = boms.filter((b) => b.is_active).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Bill of Materials (BOM) Explorer</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Inspect Finished Goods component recipes, required unit quantities, and active BOM mappings.
          </div>
        </div>
      </div>

      <div className="metrics-grid">
        <KpiCard label="Total BOM Mappings" value={boms.length} type="healthy" />
        <KpiCard label="Active BOM Entries" value={activeCount} />
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        placeholder="Search BOM by FG code, component code, or description..."
      />

      {loading ? (
        <LoadingView message="Loading BOM Explorer..." />
      ) : error ? (
        <ErrorView message={error} onRetry={fetchBOMs} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No BOM Entries Found" message="Try searching for a different Finished Good or component code." />
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th>FG Material</th>
                  <th>Component Material</th>
                  <th>Component Type</th>
                  <th>Required Qty</th>
                  <th>UOM</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((b) => (
                  <tr key={b.id}>
                    <td style={{ fontWeight: "700" }}>{b.fg_material?.code || `FG #${b.fg_material_id}`}</td>
                    <td>
                      <div style={{ fontWeight: "600" }}>{b.component_material?.code || `MAT #${b.component_material_id}`}</div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{b.component_material?.description}</div>
                    </td>
                    <td>
                      <StatusBadge status={b.component_material?.material_type || "RM"} />
                    </td>
                    <td style={{ fontWeight: "700", color: "var(--spip-red)" }}>{b.required_quantity}</td>
                    <td>{b.unit_of_measure}</td>
                    <td>
                      <StatusBadge status={b.is_active ? "HEALTHY" : "CRITICAL"} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "0.25rem 0.65rem", fontSize: "0.8rem" }}
                        onClick={() => handleExpandBOM(b.fg_material_id)}
                        disabled={expansionLoading}
                      >
                        Expand BOM Tree
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {expansionData && (
        <div className="modal-backdrop" onClick={() => setExpansionData(null)}>
          <div className="modal-content" style={{ maxWidth: "700px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem" }}>
                BOM Expansion Tree: {expansionData.fg_code}
              </h3>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem", display: "inline-flex", alignItems: "center" }}
                onClick={() => setExpansionData(null)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
              {expansionData.fg_description}
            </div>

            <h4 style={{ margin: "1rem 0 0.5rem 0", color: "var(--spip-red)", fontSize: "0.95rem" }}>
              Raw Material (RM) Components ({expansionData.rm_components.length})
            </h4>
            <div className="spip-table-container" style={{ marginBottom: "1.5rem" }}>
              <table className="spip-table">
                <thead>
                  <tr>
                    <th>Component Code</th>
                    <th>Description</th>
                    <th>Required Qty</th>
                    <th>UOM</th>
                  </tr>
                </thead>
                <tbody>
                  {expansionData.rm_components.map((rm) => (
                    <tr key={rm.id}>
                      <td style={{ fontWeight: "700" }}>{rm.component_material?.code}</td>
                      <td>{rm.component_material?.description}</td>
                      <td style={{ fontWeight: "700" }}>{rm.required_quantity}</td>
                      <td>{rm.unit_of_measure}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h4 style={{ margin: "1rem 0 0.5rem 0", color: "#d97706", fontSize: "0.95rem" }}>
              Packaging Material (PM) Components ({expansionData.pm_components.length})
            </h4>
            <div className="spip-table-container" style={{ marginBottom: "1.5rem" }}>
              <table className="spip-table">
                <thead>
                  <tr>
                    <th>Component Code</th>
                    <th>Description</th>
                    <th>Required Qty</th>
                    <th>UOM</th>
                  </tr>
                </thead>
                <tbody>
                  {expansionData.pm_components.map((pm) => (
                    <tr key={pm.id}>
                      <td style={{ fontWeight: "700" }}>{pm.component_material?.code}</td>
                      <td>{pm.component_material?.description}</td>
                      <td style={{ fontWeight: "700" }}>{pm.required_quantity}</td>
                      <td>{pm.unit_of_measure}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ textAlign: "right" }}>
              <button type="button" className="btn btn-primary" onClick={() => setExpansionData(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
