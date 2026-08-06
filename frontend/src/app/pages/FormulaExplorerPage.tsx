import { useEffect, useState } from "react";
import { formulaExplorerApi } from "../../api/services";
import type { FormulaEntry } from "../../api/types";

export function FormulaExplorerPage() {
  const [formulas, setFormulas] = useState<FormulaEntry[]>([]);
  const [selectedFormula, setSelectedFormula] = useState<FormulaEntry | null>(null);
  const [selectedModule, setSelectedModule] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    formulaExplorerApi
      .getFormulas()
      .then((data: FormulaEntry[]) => setFormulas(data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Access restricted or failed to load formulas."))
      .finally(() => setIsLoading(false));
  }, []);

  const modules = Array.from(new Set(formulas.map((f) => f.source_module)));

  const filteredFormulas = formulas.filter((f) => {
    const matchesMod = selectedModule === "ALL" || f.source_module === selectedModule;
    const matchesQ =
      !searchQuery ||
      f.formula_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.business_description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesMod && matchesQ;
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Formula Explorer</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            READ-ONLY INSPECTION CATALOG OF ALL SPIP V2 MATHEMATICAL FORMULAS & DECISION TREES
          </div>
        </div>

        <span className="badge badge-info" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
          🔒 Read-Only Admin Inspection Mode
        </span>
      </div>

      {/* Filter Toolbar */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1rem" }}>
          <div>
            <label className="form-label">Module Filter:</label>
            <select
              className="form-select"
              value={selectedModule}
              onChange={(e) => setSelectedModule(e.target.value)}
            >
              <option value="ALL">All Modules ({formulas.length})</option>
              {modules.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">Search Formula or Rule:</label>
            <input
              type="text"
              className="form-input"
              placeholder="Search by ID, name, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          Loading SPIP V2 formula registry...
        </div>
      ) : error ? (
        <div className="alert alert-error">{error}</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: selectedFormula ? "1fr 1fr" : "1fr", gap: "1.5rem" }}>
          {/* Formula Catalog Table */}
          <div className="card">
            <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Formula Catalog ({filteredFormulas.length})</h3>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Formula Name</th>
                    <th>Source Module</th>
                    <th>Version</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFormulas.map((entry) => (
                    <tr
                      key={entry.id}
                      style={{
                        backgroundColor: selectedFormula?.id === entry.id ? "rgba(5B21B6, 0.1)" : undefined,
                        cursor: "pointer",
                      }}
                      onClick={() => setSelectedFormula(entry)}
                    >
                      <td><span className="badge badge-info">{entry.id}</span></td>
                      <td><b>{entry.formula_name}</b></td>
                      <td><small>{entry.source_module}</small></td>
                      <td>{entry.last_updated_version}</td>
                      <td>
                        <button className="btn btn-secondary" style={{ padding: "0.2rem 0.5rem", fontSize: "0.8rem" }}>
                          Inspect →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Formula Detail Inspection Drawer/Panel */}
          {selectedFormula ? (
            <div className="card" style={{ borderLeft: "4px solid var(--accent-primary)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <div>
                  <span className="badge badge-info">{selectedFormula.id}</span>
                  <h3 style={{ margin: "0.25rem 0 0 0" }}>{selectedFormula.formula_name}</h3>
                </div>
                <button onClick={() => setSelectedFormula(null)} className="btn btn-secondary" style={{ padding: "0.2rem 0.5rem" }}>
                  ✕ Close
                </button>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <small style={{ color: "var(--text-muted)", textTransform: "uppercase" }}>Source Module:</small>
                <div><b>{selectedFormula.source_module}</b></div>
              </div>

              {selectedFormula.mathematical_formula ? (
                <div style={{ marginBottom: "1rem", backgroundColor: "var(--bg-card)", padding: "1rem", borderRadius: "6px", fontFamily: "monospace" }}>
                  <small style={{ color: "var(--text-muted)" }}>Mathematical Formula:</small>
                  <div style={{ fontSize: "1.1rem", fontWeight: "bold", color: "var(--accent-primary)", marginTop: "0.25rem" }}>
                    {selectedFormula.mathematical_formula}
                  </div>
                </div>
              ) : null}

              <div style={{ marginBottom: "1rem" }}>
                <small style={{ color: "var(--text-muted)" }}>Business Logic Rationale:</small>
                <p style={{ marginTop: "0.25rem", lineHeight: "1.5" }}>{selectedFormula.business_description}</p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                <div>
                  <small style={{ color: "var(--text-muted)" }}>Required Inputs:</small>
                  <ul style={{ paddingLeft: "1.2rem", marginTop: "0.25rem" }}>
                    {selectedFormula.required_inputs.map((inp, idx) => (
                      <li key={idx}><small>{inp}</small></li>
                    ))}
                  </ul>
                </div>

                <div>
                  <small style={{ color: "var(--text-muted)" }}>Generated Outputs:</small>
                  <ul style={{ paddingLeft: "1.2rem", marginTop: "0.25rem" }}>
                    {selectedFormula.generated_outputs.map((out, idx) => (
                      <li key={idx}><small>{out}</small></li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
