import React from "react";

interface StatusDistributionChartProps {
  criticalCount: number;
  warningCount: number;
  healthyCount: number;
  title?: string;
}

export const StatusDistributionChart: React.FC<StatusDistributionChartProps> = ({
  criticalCount,
  warningCount,
  healthyCount,
  title = "Planning Health Breakdown",
}) => {
  const total = criticalCount + warningCount + healthyCount;
  if (total === 0) return null;

  const criticalPct = Math.round((criticalCount / total) * 100);
  const warningPct = Math.round((warningCount / total) * 100);
  const healthyPct = 100 - criticalPct - warningPct;

  return (
    <div className="card" style={{ padding: "1.25rem" }}>
      <h3 style={{ margin: "0 0 1rem 0", fontSize: "1rem", fontWeight: "700" }}>{title}</h3>
      <div style={{ height: "16px", display: "flex", borderRadius: "8px", overflow: "hidden", background: "#e2e8f0" }}>
        {criticalCount > 0 && (
          <div
            style={{ width: `${criticalPct}%`, background: "var(--spip-red, #b51f2b)" }}
            title={`Critical: ${criticalCount} (${criticalPct}%)`}
          />
        )}
        {warningCount > 0 && (
          <div
            style={{ width: `${warningPct}%`, background: "#d97706" }}
            title={`Warning: ${warningCount} (${warningPct}%)`}
          />
        )}
        {healthyCount > 0 && (
          <div
            style={{ width: `${healthyPct}%`, background: "#16a34a" }}
            title={`Healthy: ${healthyCount} (${healthyPct}%)`}
          />
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1rem", fontSize: "0.8rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--spip-red)" }} />
          <span>Critical ({criticalCount})</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#d97706" }} />
          <span>Warning ({warningCount})</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#16a34a" }} />
          <span>Healthy ({healthyCount})</span>
        </div>
      </div>
    </div>
  );
};
