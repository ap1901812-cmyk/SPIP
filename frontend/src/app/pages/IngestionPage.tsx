import { useEffect, useState } from "react";
import { ingestionApi } from "../../api/services";
import type { SapStatusResponse, WorkbookImportReport } from "../../api/types";

export function IngestionPage() {
  const [sapStatus, setSapStatus] = useState<SapStatusResponse | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Workbook Ingestion States
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [detectedWorkbookType, setDetectedWorkbookType] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [workbookReport, setWorkbookReport] = useState<WorkbookImportReport | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    ingestionApi.getSapStatus().then((res) => setSapStatus(res)).catch(() => {});
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setWorkbookReport(null);
    setUploadError(null);

    if (file) {
      const fn = file.name.toLowerCase();
      if (fn.includes("master") || fn.includes("wb1") || fn.includes("workbook_1")) {
        setDetectedWorkbookType("Workbook 1: Master Data (Plant, Material, Vendor, Vendor-Material, Vehicle)");
      } else if (fn.includes("planning") || fn.includes("wb2") || fn.includes("workbook_2")) {
        setDetectedWorkbookType("Workbook 2: Planning Data (Inventory, Consumption, POs, PO Lines, Monthly Plan, IBP)");
      } else if (fn.includes("config") || fn.includes("wb3") || fn.includes("workbook_3")) {
        setDetectedWorkbookType("Workbook 3: SPIP Configuration (RM Totality, PM Mapping, PM Overrides)");
      } else {
        setDetectedWorkbookType("Enterprise Workbook (.xlsx - Auto-Detected on Server)");
      }
    } else {
      setDetectedWorkbookType(null);
    }
  };

  const handleSyncSap = async () => {
    setIsSyncing(true);
    setSyncResult(null);
    try {
      const res = await ingestionApi.syncSapData();
      const countsStr = Object.entries(res.synced_counts)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      setSyncResult(`SAP Data Sync Completed Successfully! (${countsStr})`);
    } catch (err: unknown) {
      setSyncResult(err instanceof Error ? err.message : "SAP Sync failed.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleWorkbookSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadError(null);
    setWorkbookReport(null);
    try {
      const res = await ingestionApi.uploadWorkbook(selectedFile, replaceExisting);
      setWorkbookReport(res);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Workbook upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Enterprise Data Ingestion & Integration</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            NATIVE EXCEL (.XLSX) WORKBOOK INGESTION & SAP ADAPTER INTERFACE
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: "1.5rem" }}>
        {/* Section 1: Enterprise Workbook Upload */}
        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--spip-red-dark)" }}>1. Enterprise Excel Workbook Import (.xlsx)</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Upload complete multi-sheet enterprise workbooks for Master Data, Planning Data, or SPIP Configuration.
          </p>

          {uploadError && <div className="alert alert-error">{uploadError}</div>}

          <form onSubmit={handleWorkbookSubmit}>
            <div className="form-group">
              <label className="form-label">Select Native Excel Workbook (.xlsx)</label>
              <input
                type="file"
                className="form-input"
                accept=".xlsx"
                onChange={handleFileChange}
                required
              />
            </div>

            {detectedWorkbookType && (
              <div
                style={{
                  background: "var(--surface-subtle)",
                  padding: "0.75rem",
                  borderRadius: "6px",
                  border: "1px solid var(--border)",
                  marginBottom: "1rem",
                  fontSize: "0.85rem",
                }}
              >
                <strong>Detected Type:</strong>{" "}
                <span style={{ color: "var(--spip-red-dark)", fontWeight: 600 }}>{detectedWorkbookType}</span>
              </div>
            )}

            <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <input
                type="checkbox"
                id="replaceExisting"
                checked={replaceExisting}
                onChange={(e) => setReplaceExisting(e.target.checked)}
              />
              <label htmlFor="replaceExisting" className="form-label" style={{ margin: 0, cursor: "pointer" }}>
                <strong>Replace Existing Business Data</strong> (Clears previous business tables before import for clean UAT runs)
              </label>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isUploading || !selectedFile}
              style={{ width: "100%", marginTop: "0.5rem" }}
            >
              {isUploading ? "Parsing & Validating Workbook Transaction..." : "Upload & Process Workbook"}
            </button>
          </form>

          {/* Report Summary & Header Detection Display */}
          {workbookReport && (
            <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <div className="alert alert-success" style={{ marginBottom: "1rem" }}>
                <div>
                  <strong>{workbookReport.workbook_type}</strong> imported successfully in{" "}
                  {workbookReport.execution_time_ms} ms!
                </div>
                <div style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                  Total Imported: <strong>{workbookReport.total_imported}</strong> | Total Updated:{" "}
                  <strong>{workbookReport.total_updated}</strong> | Total Rejected:{" "}
                  <strong>{workbookReport.total_rejected}</strong>
                </div>
              </div>

              {/* Automatic Header Detection Report Card */}
              <div
                style={{
                  background: "var(--surface-subtle)",
                  borderRadius: "6px",
                  padding: "1rem",
                  marginBottom: "1.5rem",
                  border: "1px solid var(--border)",
                }}
              >
                <h4 style={{ margin: "0 0 0.5rem 0", color: "var(--spip-red-dark)", fontSize: "0.9rem" }}>
                  Automatic Header Mapping Report
                </h4>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
                  <strong>Detected Workbook:</strong> {workbookReport.workbook_type} <br />
                  <strong>Detected Sheets:</strong> {workbookReport.sheets_summary.map((s) => s.sheet_name).join(", ")}
                </div>

                <div style={{ maxHeight: "200px", overflowY: "auto" }}>
                  {workbookReport.sheets_summary.map((sheet, sIdx) => (
                    <div key={sIdx} style={{ marginBottom: "0.75rem" }}>
                      <div style={{ fontWeight: 600, fontSize: "0.8rem", marginBottom: "0.25rem" }}>
                        Sheet: {sheet.sheet_name}
                      </div>
                      <table className="data-table" style={{ fontSize: "0.75rem" }}>
                        <thead>
                          <tr>
                            <th>Excel Header</th>
                            <th>→</th>
                            <th>Internal Field</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sheet.header_mappings?.map((m, mIdx) => (
                            <tr key={mIdx}>
                              <td style={{ color: "var(--spip-red-dark)", fontFamily: "monospace" }}>{m.raw_header}</td>
                              <td>→</td>
                              <td style={{ color: "var(--status-healthy-text)", fontFamily: "monospace", fontWeight: 600 }}>
                                {m.mapped_field}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              </div>

              <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem" }}>Sheet Import Detail Report:</h4>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table" style={{ fontSize: "0.8rem" }}>
                  <thead>
                    <tr>
                      <th>Sheet Name</th>
                      <th>Imported</th>
                      <th>Updated</th>
                      <th>Rejected</th>
                      <th>Warnings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workbookReport.sheets_summary.map((sheet, idx) => (
                      <tr key={idx}>
                        <td>
                          <strong>{sheet.sheet_name}</strong>
                        </td>
                        <td style={{ color: "var(--status-healthy-text)", fontWeight: 600 }}>{sheet.imported}</td>
                        <td style={{ color: "var(--status-warning-text)" }}>{sheet.updated}</td>
                        <td style={{ color: sheet.rejected > 0 ? "var(--status-critical-text)" : "inherit" }}>
                          {sheet.rejected}
                        </td>
                        <td>
                          {sheet.warnings.length > 0 ? (
                            <span style={{ color: "var(--status-warning-text)" }}>
                              {sheet.warnings.length} warning(s)
                            </span>
                          ) : (
                            <span style={{ color: "var(--text-muted)" }}>Clean</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Section 2: SAP Adapter Synchronization */}
        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--spip-red-dark)" }}>2. SAP Adapter Synchronization</h3>

          {sapStatus && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.5rem" }}>
                <strong>Adapter Mode:</strong>
                <span className="user-role-badge" style={{ background: "var(--surface-subtle)", color: "var(--text-main)" }}>
                  {sapStatus.adapter_mode.toUpperCase()}
                </span>
                {sapStatus.is_mock && <span className="badge-status HEALTHY">Mock Mode</span>}
              </div>
              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {sapStatus.message}
              </p>
            </div>
          )}

          {syncResult && (
            <div className="alert alert-success" style={{ marginBottom: "1rem" }}>
              {syncResult}
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            disabled={isSyncing}
            onClick={handleSyncSap}
            style={{ width: "100%" }}
          >
            {isSyncing ? "Synchronizing SAP Entities..." : "Trigger Full SAP Sync"}
          </button>
        </div>
      </div>
    </div>
  );
}
