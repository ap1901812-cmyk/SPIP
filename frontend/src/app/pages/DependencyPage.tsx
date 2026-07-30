import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { dependencyApi, domainApi } from "../../api/services";
import type { Material, MaterialDependencyResponse, WhereUsedResponse } from "../../api/types";
import { FilterBar } from "../../components/FilterBar";
import { KpiCard } from "../../components/KpiCard";
import { EmptyState, ErrorView, LoadingView } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

export const DependencyPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchFromUrl = searchParams.get("search") || "";

  const [searchTerm, setSearchTerm] = useState(searchFromUrl);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState<number | null>(null);

  const [whereUsedData, setWhereUsedData] = useState<WhereUsedResponse | null>(null);
  const [dependencyData, setDependencyData] = useState<MaterialDependencyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMaterials = async () => {
    try {
      const res = await domainApi.getMaterials();
      setMaterials(res);
      if (res.length > 0 && !selectedMaterialId) {
        setSelectedMaterialId(res[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDependencies = async (materialId: number) => {
    try {
      setLoading(true);
      setError(null);
      const [wuRes, depRes] = await Promise.all([
        dependencyApi.getWhereUsed(materialId),
        dependencyApi.getDependencies(materialId),
      ]);
      setWhereUsedData(wuRes);
      setDependencyData(depRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load material dependencies.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterials();
  }, []);

  useEffect(() => {
    if (selectedMaterialId) {
      fetchDependencies(selectedMaterialId);
    }
  }, [selectedMaterialId]);

  const handleSearchChange = (val: string) => {
    setSearchTerm(val);
    const newParams = new URLSearchParams(searchParams);
    if (val) newParams.set("search", val);
    else newParams.delete("search");
    setSearchParams(newParams);
  };

  const filteredMaterials = materials.filter((m) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return m.code.toLowerCase().includes(term) || m.description.toLowerCase().includes(term);
  });

  const formatMaterialType = (type?: string): string => {
    if (!type) return "N/A";
    const upper = type.toUpperCase();
    if (upper === "RAW_MATERIAL" || upper === "RAW MATERIAL" || upper === "RM") return "RM";
    if (upper === "PACKAGING" || upper === "PACKAGING MATERIAL" || upper === "PM") return "PM";
    if (upper === "FINISHED_GOOD" || upper === "FINISHED GOOD" || upper === "FG") return "FG";
    return type;
  };

  const selectedMaterial = materials.find((m) => m.id === selectedMaterialId);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Where-Used & Dependency Analysis</h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Identify parent Finished Goods dependent on raw & packaging components, and analyze downstream component recipes.
          </div>
        </div>
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        placeholder="Filter material selection..."
      />

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Select Target Material to Analyze:</label>
          <select
            className="form-select"
            value={selectedMaterialId || ""}
            onChange={(e) => setSelectedMaterialId(Number(e.target.value))}
          >
            {filteredMaterials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.code} - {m.description} ({formatMaterialType(m.material_type)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingView message="Analyzing Material Dependencies & Where-Used Relationships..." />
      ) : error ? (
        <ErrorView message={error} onRetry={() => selectedMaterialId && fetchDependencies(selectedMaterialId)} />
      ) : !selectedMaterial ? (
        <EmptyState title="No Material Selected" message="Select a material above to perform dependency analysis." />
      ) : (
        <>
          <div className="metrics-grid">
            <KpiCard label="Target Material" value={selectedMaterial.code} subtitle={selectedMaterial.description} />
            <KpiCard label="Classification" value={formatMaterialType(selectedMaterial.material_type)} />
            <KpiCard label="Upstream FGs Count" value={whereUsedData?.total_where_used || 0} type="healthy" subtitle="Where Used Count" />
            <KpiCard label="Downstream Components" value={dependencyData?.downstream_components.length || 0} subtitle="BOM Recipes" />
          </div>

          {/* Upstream Where-Used Table */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
              Where-Used: Parent Finished Goods Consuming {selectedMaterial.code}
            </h3>
            {!whereUsedData || whereUsedData.where_used.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No Finished Goods currently consume or depend on this component material.</div>
            ) : (
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>BOM ID</th>
                      <th>FG Code</th>
                      <th>FG Description</th>
                      <th>Classification</th>
                      <th>Required Qty per Unit</th>
                      <th>Component UOM</th>
                      <th>BOM Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {whereUsedData.where_used.map((wu) => (
                      <tr key={wu.bom_id}>
                        <td>#{wu.bom_id}</td>
                        <td style={{ fontWeight: "700" }}>{wu.fg_code}</td>
                        <td>{wu.fg_description}</td>
                        <td>
                          <StatusBadge status={wu.fg_material_type} />
                        </td>
                        <td style={{ fontWeight: "700", color: "var(--spip-red)" }}>{wu.required_quantity}</td>
                        <td>{wu.unit_of_measure}</td>
                        <td>
                          <StatusBadge status={wu.is_active ? "HEALTHY" : "CRITICAL"} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Downstream Components Table if material is an FG */}
          {dependencyData && dependencyData.downstream_components.length > 0 && (
            <div className="card">
              <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", fontWeight: "700" }}>
                Downstream Component Recipes for {selectedMaterial.code}
              </h3>
              <div className="spip-table-container">
                <table className="spip-table">
                  <thead>
                    <tr>
                      <th>BOM ID</th>
                      <th>Component Code</th>
                      <th>Description</th>
                      <th>Type</th>
                      <th>Required Qty</th>
                      <th>Component UOM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dependencyData.downstream_components.map((comp) => (
                      <tr key={comp.bom_id}>
                        <td>#{comp.bom_id}</td>
                        <td style={{ fontWeight: "700" }}>{comp.fg_code}</td>
                        <td>{comp.fg_description}</td>
                        <td>
                          <StatusBadge status={comp.fg_material_type} />
                        </td>
                        <td style={{ fontWeight: "700" }}>{comp.required_quantity}</td>
                        <td>{comp.unit_of_measure}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
