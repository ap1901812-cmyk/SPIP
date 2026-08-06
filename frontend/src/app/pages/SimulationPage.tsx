import { useEffect, useState } from "react";
import { domainApi, simulationApi } from "../../api/services";
import type { Plant, SimulationRunItem } from "../../api/types";

export function SimulationPage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<string>("");
  const [materialCode, setMaterialCode] = useState<string>("RM-101");
  const [scenarioName, setScenarioName] = useState<string>("Demand Surge +25%");

  // Scenario Overrides
  const [inventoryOverride, setInventoryOverride] = useState<string>("");
  const [demandMultiplier, setDemandMultiplier] = useState<number>(1.25);
  const [leadTimeOverride, setLeadTimeOverride] = useState<string>("");
  const [safetyStockMultiplier, setSafetyStockMultiplier] = useState<number>(1.0);

  const [history, setHistory] = useState<SimulationRunItem[]>([]);
  const [activeSimulation, setActiveSimulation] = useState<SimulationRunItem | null>(null);

  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainApi
      .getPlants()
      .then((p: Plant[]) => {
        setPlants(p);
        if (p.length > 0) setSelectedPlant(p[0].code);
      })
      .catch(() => {});

    loadHistory();
  }, []);

  const loadHistory = () => {
    simulationApi
      .getSimulations()
      .then((h: SimulationRunItem[]) => setHistory(h))
      .catch(() => {});
  };

  const handleRunSimulation = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    setError(null);

    const payload = {
      scenario_name: scenarioName,
      plant_code: selectedPlant,
      material_code: materialCode || undefined,
      overrides: {
        inventory_override_qty: inventoryOverride ? parseFloat(inventoryOverride) : undefined,
        demand_multiplier: demandMultiplier,
        lead_time_override_days: leadTimeOverride ? parseFloat(leadTimeOverride) : undefined,
        safety_stock_multiplier: safetyStockMultiplier,
      },
    };

    simulationApi
      .runSimulation(payload)
      .then((res: SimulationRunItem) => {
        setActiveSimulation(res);
        loadHistory();
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Simulation execution failed."))
      .finally(() => setIsSimulating(false));
  };

  const inspectSimulation = (id: number) => {
    simulationApi
      .getSimulation(id)
      .then((res: SimulationRunItem) => setActiveSimulation(res))
      .catch(() => {});
  };

  const impact = activeSimulation?.results?.simulation_impact_summary;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">What-If Scenario Simulation Engine</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            ISOLATED PLANNING PIPELINE SIMULATION (ZERO PRODUCTION DB SIDE-EFFECTS)
          </div>
        </div>

        <span className="badge badge-info" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
          🛡️ Isolated Sandbox Execution
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Scenario Builder Form */}
        <div className="card">
          <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Scenario Builder</h3>
          <form onSubmit={handleRunSimulation}>
            <div style={{ marginBottom: "1rem" }}>
              <label className="form-label">Scenario Name:</label>
              <input
                type="text"
                className="form-input"
                required
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label className="form-label">Plant:</label>
                <select
                  className="form-select"
                  value={selectedPlant}
                  onChange={(e) => setSelectedPlant(e.target.value)}
                >
                  {plants.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.code} ({p.name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="form-label">Material Code:</label>
                <input
                  type="text"
                  className="form-input"
                  value={materialCode}
                  onChange={(e) => setMaterialCode(e.target.value)}
                />
              </div>
            </div>

            <hr style={{ border: 0, borderTop: "1px solid var(--border)", margin: "1rem 0" }} />

            <h4 style={{ margin: "0 0 0.75rem 0" }}>Scenario Parameter Overrides</h4>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label className="form-label">Demand Multiplier:</label>
                <select
                  className="form-select"
                  value={demandMultiplier}
                  onChange={(e) => setDemandMultiplier(parseFloat(e.target.value))}
                >
                  <option value={0.75}>-25% Demand Reduction</option>
                  <option value={1.0}>Baseline (1.0x)</option>
                  <option value={1.25}>+25% Demand Surge (1.25x)</option>
                  <option value={1.5}>+50% Demand Surge (1.5x)</option>
                  <option value={2.0}>+100% Demand Spike (2.0x)</option>
                </select>
              </div>

              <div>
                <label className="form-label">Safety Stock Multiplier:</label>
                <select
                  className="form-select"
                  value={safetyStockMultiplier}
                  onChange={(e) => setSafetyStockMultiplier(parseFloat(e.target.value))}
                >
                  <option value={0.8}>0.8x Buffer Reduction</option>
                  <option value={1.0}>1.0x Standard Buffer</option>
                  <option value={1.5}>1.5x Buffer Elevation</option>
                  <option value={2.0}>2.0x High Buffer</option>
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
              <div>
                <label className="form-label">Simulated Usable Stock (KG):</label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="Leave blank for baseline"
                  value={inventoryOverride}
                  onChange={(e) => setInventoryOverride(e.target.value)}
                />
              </div>

              <div>
                <label className="form-label">Simulated Lead Time (Days):</label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="Leave blank for baseline"
                  value={leadTimeOverride}
                  onChange={(e) => setLeadTimeOverride(e.target.value)}
                />
              </div>
            </div>

            {error ? <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div> : null}

            <button type="submit" disabled={isSimulating} className="btn btn-primary" style={{ width: "100%" }}>
              {isSimulating ? "Executing Isolated Pipeline Simulation..." : "🚀 Run What-If Scenario Simulation"}
            </button>
          </form>
        </div>

        {/* Simulation Impact & Scenario Comparison Panel */}
        <div>
          {activeSimulation && impact ? (
            <div className="card" style={{ borderLeft: "4px solid var(--accent-primary)", marginBottom: "1.5rem" }}>
              <h3 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Simulation Results Comparison</h3>
              <div className="eyebrow" style={{ marginBottom: "1rem" }}>
                SCENARIO: {activeSimulation.scenario_name} ({activeSimulation.plant_code})
              </div>

              <table className="data-table">
                <tbody>
                  <tr>
                    <td><b>Simulated Available Stock</b></td>
                    <td><b>{impact.simulated_available_inventory?.toLocaleString()} KG</b></td>
                  </tr>
                  <tr>
                    <td><b>Simulated Daily Demand</b></td>
                    <td>{impact.simulated_daily_demand?.toLocaleString()} KG/day</td>
                  </tr>
                  <tr>
                    <td><b>Simulated Safety Stock Target</b></td>
                    <td>{impact.simulated_safety_stock_target?.toLocaleString()} KG</td>
                  </tr>
                  <tr>
                    <td><b>15-Day Horizon Requirement</b></td>
                    <td>{impact.simulated_15_day_horizon_requirement?.toLocaleString()} KG</td>
                  </tr>
                  <tr>
                    <td><b>Net Procurement Deficit</b></td>
                    <td>
                      <b style={{ color: impact.simulated_net_procurement_deficit > 0 ? "var(--status-critical-text)" : "var(--status-healthy-text)" }}>
                        {impact.simulated_net_procurement_deficit?.toLocaleString()} KG
                      </b>
                    </td>
                  </tr>
                  <tr>
                    <td><b>Simulated Priority Classification</b></td>
                    <td>
                      <span className={`badge ${impact.simulated_priority === "CRITICAL" ? "badge-error" : impact.simulated_priority === "HIGH" ? "badge-warning" : "badge-info"}`}>
                        {impact.simulated_priority}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
              Select or run a simulation scenario to compare results against baseline production planning.
            </div>
          )}

          {/* Scenario History List */}
          <div className="card">
            <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Simulation History ({history.length})</h3>
            <div style={{ overflowY: "auto", maxHeight: "300px" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ref</th>
                    <th>Scenario Name</th>
                    <th>Plant</th>
                    <th>Material</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h: SimulationRunItem) => (
                    <tr key={h.id}>
                      <td>#{h.id}</td>
                      <td><b>{h.scenario_name}</b></td>
                      <td>{h.plant_code}</td>
                      <td>{h.material_code || "ALL"}</td>
                      <td>
                        <button
                          onClick={() => inspectSimulation(h.id)}
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.5rem", fontSize: "0.8rem" }}
                        >
                          Compare →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
