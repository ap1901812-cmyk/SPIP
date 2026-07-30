import { useEffect, useState } from "react";
import { ingestionApi } from "../../api/services";
import type { IngestionResult, SapStatusResponse } from "../../api/types";

export function IngestionPage() {
  const [sapStatus, setSapStatus] = useState<SapStatusResponse | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // File import states
  const [entityType, setEntityType] = useState<"consumption" | "inventory">("consumption");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [importResult, setImportResult] = useState<IngestionResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    ingestionApi.getSapStatus().then((res) => setSapStatus(res)).catch(() => {});
  }, []);

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

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadError(null);
    setImportResult(null);
    try {
      const res = await ingestionApi.uploadFile(selectedFile, entityType);
      setImportResult(res);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "File upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Ingestion & SAP Integration</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            EXCEL / CSV IMPORT SERVICE & SAP ADAPTER INTERFACE
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: "1.5rem" }}>
        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--spip-red-dark)" }}>1. SAP Adapter Synchronization</h3>

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
          >
            {isSyncing ? "Synchronizing SAP Entities..." : "Trigger Full SAP Sync"}
          </button>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--spip-red-dark)" }}>2. Excel / CSV File Import</h3>

          {uploadError && <div className="alert alert-error">{uploadError}</div>}

          <form onSubmit={handleUploadSubmit}>
            <div className="form-group">
              <label className="form-label">Target Entity Type</label>
              <select
                className="form-select"
                value={entityType}
                onChange={(e) => setEntityType(e.target.value as "consumption" | "inventory")}
              >
                <option value="consumption">Consumption History (plant_code, material_code, date, quantity)</option>
                <option value="inventory">Inventory Snapshots (plant_code, material_code, usable_stock)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Select File (.csv or .xlsx)</label>
              <input
                type="file"
                className="form-input"
                accept=".csv, .xlsx"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isUploading || !selectedFile}
            >
              {isUploading ? "Validating & Importing..." : "Upload & Process File"}
            </button>
          </form>

          {importResult && (
            <div style={{ marginTop: "1.25rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <div className={importResult.success ? "alert alert-success" : "alert alert-error"}>
                <strong>Import Result:</strong> {importResult.imported_records} of {importResult.total_rows} rows imported successfully.
              </div>

              {importResult.errors.length > 0 && (
                <div>
                  <div className="eyebrow" style={{ color: "var(--status-critical-text)", marginBottom: "0.35rem" }}>
                    ROW VALIDATION ERRORS ({importResult.errors.length}):
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.8rem", color: "var(--status-critical-text)" }}>
                    {importResult.errors.map((err, idx) => (
                      <li key={idx}>
                        Row {err.row} [{err.field}]: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
