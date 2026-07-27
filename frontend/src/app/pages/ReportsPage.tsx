import { useEffect, useState } from "react";
import { domainApi, reportsApi } from "../../api/services";
import type { Plant } from "../../api/types";

export function ReportsPage() {
  const [reportType, setReportType] = useState<string>("planning_summary");
  const [format, setFormat] = useState<"xlsx" | "csv">("xlsx");
  const [plants, setPlants] = useState<Plant[]>([]);
  const [plantCode, setPlantCode] = useState<string>("");
  const [materialCode, setMaterialCode] = useState<string>("");
  const [criticalityStatus, setCriticalityStatus] = useState<string>("");
  const [allocationStatus, setAllocationStatus] = useState<string>("");

  const [previewData, setPreviewData] = useState<{
    title: string;
    headers: string[];
    rows: (string | number)[][];
    total_records: number;
  } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

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
    setExportMessage(null);
    reportsApi
      .getPreview(
        reportType,
        plantCode || undefined,
        materialCode || undefined,
        criticalityStatus || undefined,
        allocationStatus || undefined
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
  }, [reportType, plantCode, materialCode, criticalityStatus, allocationStatus]);

  const loadPreview = () => {
    setIsLoading(true);
    setError(null);
    setExportMessage(null);
    reportsApi
      .getPreview(
        reportType,
        plantCode || undefined,
        materialCode || undefined,
        criticalityStatus || undefined,
        allocationStatus || undefined
      )
      .then((data) => setPreviewData(data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load report preview."))
      .finally(() => setIsLoading(false));
  };


  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    setExportMessage(null);
    try {
      const job = await reportsApi.requestExport({
        report_type: reportType,
        format,
        plant_code: plantCode || undefined,
        material_code: materialCode || undefined,
        criticality_status: criticalityStatus || undefined,
        status: allocationStatus || undefined,
      });

      // Authorized download via fetch with bearer token
      const token = localStorage.getItem("spip_token");
      const downloadRes = await fetch(job.download_url, {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      });

      if (!downloadRes.ok) {
        throw new Error(`Download failed with status ${downloadRes.status}`);
      }

      const blob = await downloadRes.blob();
      const filename =
        downloadRes.headers
          .get("content-disposition")
          ?.split("filename=")[1]
          ?.replace(/"/g, "") || `${reportType}.${format}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setExportMessage(`Successfully exported ${filename}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report export failed.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports & Analytics Export</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            ENTERPRISE CONSOLIDATED XLSX & CSV REPORTING
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? "Generating Export..." : `Export File (${format.toUpperCase()})`}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {exportMessage && <div className="alert alert-success">{exportMessage}</div>}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
          <div>
            <label className="form-label" htmlFor="report-type-select">
              Report Type
            </label>
            <select
              id="report-type-select"
              className="form-input"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              <option value="planning_summary">Inventory & Planning Summary</option>
              <option value="forecast_summary">Demand Forecast Summary</option>
              <option value="allocations">Vendor Allocations</option>
            </select>
          </div>

          <div>
            <label className="form-label" htmlFor="format-select">
              Export Format
            </label>
            <select
              id="format-select"
              className="form-input"
              value={format}
              onChange={(e) => setFormat(e.target.value as "xlsx" | "csv")}
            >
              <option value="xlsx">Excel Workbook (.xlsx)</option>
              <option value="csv">CSV Spreadsheet (.csv)</option>
            </select>
          </div>

          <div>
            <label className="form-label" htmlFor="plant-filter-select">
              Plant Location
            </label>
            <select
              id="plant-filter-select"
              className="form-input"
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
            <label className="form-label" htmlFor="material-filter-input">
              Material Code Filter
            </label>
            <input
              id="material-filter-input"
              type="text"
              className="form-input"
              placeholder="e.g. MAT-1001"
              value={materialCode}
              onChange={(e) => setMaterialCode(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") loadPreview();
              }}
            />
          </div>

          {reportType === "planning_summary" && (
            <div>
              <label className="form-label" htmlFor="criticality-filter-select">
                Criticality Filter
              </label>
              <select
                id="criticality-filter-select"
                className="form-input"
                value={criticalityStatus}
                onChange={(e) => setCriticalityStatus(e.target.value)}
              >
                <option value="">All Criticalities</option>
                <option value="CRITICAL">CRITICAL Only</option>
                <option value="WARNING">WARNING Only</option>
                <option value="HEALTHY">HEALTHY Only</option>
              </select>
            </div>
          )}

          {reportType === "allocations" && (
            <div>
              <label className="form-label" htmlFor="status-filter-select">
                Allocation Status
              </label>
              <select
                id="status-filter-select"
                className="form-input"
                value={allocationStatus}
                onChange={(e) => setAllocationStatus(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="DRAFT">DRAFT</option>
                <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
                <option value="APPROVED">APPROVED</option>
                <option value="REJECTED">REJECTED</option>
              </select>
            </div>
          )}
        </div>

        <div style={{ marginTop: "1rem", textAlign: "right" }}>
          <button type="button" className="btn btn-secondary" onClick={loadPreview}>
            Refresh Preview
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
          Generating report preview...
        </div>
      ) : !previewData || previewData.rows.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <h3 style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>No Report Data Found</h3>
          <p className="text-secondary">Try adjusting your filters or selecting a different report type.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>{previewData.title}</h3>
            <span className="badge badge-neutral">{previewData.total_records} Records</span>
          </div>
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
                {previewData.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} style={{ whiteSpace: "nowrap" }}>
                        {cell === null || cell === "" ? "-" : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
