import React from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  type?: "critical" | "warning" | "healthy" | "default";
  subtitle?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({ label, value, type = "default", subtitle }) => {
  const cardClass = `metric-card ${type !== "default" ? type : ""}`;
  return (
    <div className={cardClass}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {subtitle && <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>{subtitle}</div>}
    </div>
  );
};
