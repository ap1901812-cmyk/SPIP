import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { domainApi, forecastingApi } from "../../api/services";
import type { ForecastCalculationResult, Material, Plant } from "../../api/types";

export function ForecastingPage() {
  const [searchParams] = useSearchParams();
  const initialMaterial = searchParams.get("material") || "MAT-1001";
  const initialPlant = searchParams.get("plant") || "PLANT-1000";

  const [plants, setPlants] = useState<Plant[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<string>(initialPlant);
  const [selectedMaterial, setSelectedMaterial] = useState<string>(initialMaterial);
  const [horizonDays, setHorizonDays] = useState<number>(12);

  const [forecast, setForecast] = useState<ForecastCalculationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainApi.getPlants().then((p) => setPlants(p)).catch(() => {});
    domainApi.getMaterials().then((m) => setMaterials(m)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedMaterial || !selectedPlant) return;
    setIsLoading(true);
    setError(null);
    forecastingApi
      .getMaterialForecast(selectedMaterial, selectedPlant, horizonDays)
      .then((res) => setForecast(res))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to generate demand forecast.")
      )
      .finally(() => setIsLoading(false));
  }, [selectedMaterial, selectedPlant, horizonDays]);

  const maxVal = forecast
    ? Math.max(...forecast.point_forecasts.map((p) => p.forecasted_quantity), 1)
    : 1;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">V1 Demand Forecasting Engine</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            TIME-AWARE BACKTESTED CANDIDATE MODEL SELECTION
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <div>
            <label className="form-label" style={{ margin: 0, fontSize: "0.75rem" }}>
              Plant
            </label>
            <select
              className="form-select"
              value={selectedPlant}
              onChange={(e) => setSelectedPlant(e.target.value)}
              style={{ width: "auto" }}
            >
              {plants.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.code}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ margin: 0, fontSize: "0.75rem" }}>
              Material
            </label>
            <select
              className="form-select"
              value={selectedMaterial}
              onChange={(e) => setSelectedMaterial(e.target.value)}
              style={{ width: "auto" }}
            >
              {materials.map((m) => (
                <option key={m.code} value={m.code}>
                  {m.code} ({m.description})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ margin: 0, fontSize: "0.75rem" }}>
              Horizon
            </label>
            <select
              className="form-select"
              value={horizonDays}
              onChange={(e) => setHorizonDays(Number(e.target.value))}
              style={{ width: "auto" }}
            >
              <option value={7}>7 Days</option>
              <option value={12}>12 Days</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          Executing time-series backtests & model selection...
        </div>
      ) : error || !forecast ? (
        <div className="alert alert-error">{error || "No forecast available."}</div>
      ) : (
        <div>
          {forecast.is_fallback && (
            <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
              <strong>Deterministic Fallback Active:</strong> {forecast.fallback_reason}
            </div>
          )}

          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Selected Model</div>
              <div className="metric-value" style={{ fontSize: "1.25rem", color: "var(--spip-red-dark)" }}>
                {forecast.selected_model}
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Backtest WMAPE Error</div>
              <div className="metric-value">
                {(forecast.evaluation_metric_value * 100).toFixed(1)}%
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Total Demand Projection</div>
              <div className="metric-value">
                {forecast.total_forecasted_demand.toLocaleString()} {forecast.base_uom}
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Avg Daily Forecast</div>
              <div className="metric-value">
                {forecast.average_forecasted_daily_demand.toLocaleString()} {forecast.base_uom}/day
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0, marginBottom: "1.25rem" }}>
              Point Forecast Projections ({forecast.forecast_horizon_days} Days)
            </h3>

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "0.5rem",
                height: "160px",
                padding: "1rem 0.5rem",
                background: "var(--surface-subtle)",
                borderRadius: "0.375rem",
                marginBottom: "1.5rem",
              }}
            >
              {forecast.point_forecasts.map((pt) => {
                const heightPct = Math.max(10, (pt.forecasted_quantity / maxVal) * 100);
                return (
                  <div
                    key={pt.day_offset}
                    style={{
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      height: "100%",
                      justifyContent: "flex-end",
                    }}
                  >
                    <div style={{ fontSize: "0.7rem", fontWeight: "600", marginBottom: "0.2rem" }}>
                      {pt.forecasted_quantity}
                    </div>
                    <div
                      style={{
                        width: "100%",
                        height: `${heightPct}%`,
                        background: "var(--spip-red)",
                        borderRadius: "0.25rem 0.25rem 0 0",
                        transition: "height 0.3s ease",
                      }}
                      title={`Day ${pt.day_offset}: ${pt.forecasted_quantity} ${pt.uom}`}
                    />
                    <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                      D+{pt.day_offset}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="spip-table-container">
              <table className="spip-table">
                <thead>
                  <tr>
                    <th>Day Offset</th>
                    <th>Forecast Date</th>
                    <th>Forecasted Daily Quantity</th>
                    <th>Unit of Measure</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.point_forecasts.map((pt) => (
                    <tr key={pt.day_offset}>
                      <td>
                        <strong>Day +{pt.day_offset}</strong>
                      </td>
                      <td>{pt.forecast_date}</td>
                      <td>
                        <strong>
                          {pt.forecasted_quantity.toLocaleString()} {pt.uom}
                        </strong>
                      </td>
                      <td>{pt.uom}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
