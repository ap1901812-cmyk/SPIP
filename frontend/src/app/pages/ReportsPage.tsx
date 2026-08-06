import { useEffect, useState } from "react";
import { domainApi, reportsApi } from "../../api/services";
import type { Plant } from "../../api/types";

const REPORT_TYPES = [
  { id: "planning_summary", label: "1. Planning Summary Report" },
  { id: "planning_readiness", label: "2. Planning Readiness Report" },
  { id: "consumption_intelligence", label: "3. Consumption Intelligence Report" },
  { id: "inventory_intelligence", label: "4. Inventory Intelligence Report" },
  { id: "forecast_performance", label: "5. Forecast Performance Report" },
  { id: "requirement_resolution", label: "6. Requirement Resolution Report" },
  { id: "rm_totality", label: "7. RM Totality Report" },
  { id: "pm_override", label: "8. PM Override Report" },
  { id: "dependency", label: "9. Dependency Intelligence Report" },
  { id: "production_readiness", label: "10. Production Readiness Report" },
  { id: "procurement_recommendation", label: "11. Procurement Recommendation Report" },
  { id: "allocation", label: "12. Procurement Allocation Report" },
  { id: "simulation", label: "13. What-If Simulation Report" },
];

export function ReportsPage() {
  const [reportType, setReportType] = useState<string>("planning_summary");
  const [plants, setPlants] = useState<Plant[]>([]);
  const [plantCode, setPlantCode] = useState<string>("");
  const [materialCode, setMaterialCode] = useState<string>("");

  const [previewData, setPreviewData] = useState<{
    title: string;
    headers: string[];
    rows: (string | number)[][];
    total_records: number;
  } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainApi
      .getPlants()
      .then((p) => setPlants(p))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    reportsApi
      .getPreview(
        reportType,
        plantCode || undefined,
        materialCode || undefined
      )
      .then((data) => {
        if (isMounted) setPreviewData(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load report preview.");
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [reportType, plantCode, materialCode]);

  const handleDownload = (fmt: "csv" | "xlsx" | "pdf") => {
    const url = `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/reports/export?report_type=${reportType}&format=${fmt}${plantCode ? `&plant_code=${plantCode}` : ""}${materialCode ? `&material_code=${materialCode}` : ""}`;
    window.open(url, "_blank");
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">SPIP V2 Enterprise Reports & Analytics</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            EXECUTIVE REPORTING & DATASET EXPORT ENGINE
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "1rem", alignItems: "end" }}>
          <div>
            <label className="form-label">Report Category:</label>
            <select
              className="form-select"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              {REPORT_TYPES.map((rt) => (
                <option key={rt.id} value={rt.id}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">Filter Plant:</label>
            <select
              className="form-select"
              value={plantCode}
              onChange={(e) => setPlantCode(e.target.value)}
            >
              <option value="">All Plants</option>
              {plants.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.code} ({p.name})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">Material Filter:</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. RM-101"
              value={materialCode}
              onChange={(e) => setMaterialCode(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Export Toolbar & Data Preview */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h3 style={{ margin: 0 }}>{previewData ? previewData.title : "Report Dataset Preview"}</h3>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              {previewData ? `${previewData.total_records} record(s) loaded` : ""}
            </span>
          </div>

          {/* Export Action Buttons */}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => handleDownload("csv")}
              className="btn btn-secondary"
              style={{ fontSize: "0.85rem" }}
            >
              📥 Export CSV
            </button>
            <button
              onClick={() => handleDownload("xlsx")}
              className="btn btn-secondary"
              style={{ fontSize: "0.85rem" }}
            >
              📊 Export Excel (XLSX)
            </button>
            <button
              onClick={() => handleDownload("pdf")}
              className="btn btn-primary"
              style={{ fontSize: "0.85rem" }}
            >
              📄 Export PDF Report
            </button>
          </div>
        </div>

        {isLoading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            Fetching enterprise report dataset...
          </div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : previewData && previewData.rows.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  {previewData.headers.map((h, i) => (
                    <th key={i}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.rows.map((row, idx) => (
                  <tr key={idx}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx}>{cell !== null && cell !== undefined ? String(cell) : ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            No records found for this report configuration.
          </div>
        )}
      </div>
    </div>
  );
}
