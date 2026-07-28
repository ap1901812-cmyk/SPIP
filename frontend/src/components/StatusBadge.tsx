import React from "react";

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normalized = status ? status.toUpperCase() : "UNKNOWN";
  let badgeClass = "badge-status ";

  if (normalized === "CRITICAL" || normalized === "REJECTED") {
    badgeClass += "CRITICAL";
  } else if (normalized === "WARNING" || normalized === "AT_RISK" || normalized === "PENDING_APPROVAL") {
    badgeClass += "WARNING";
  } else if (normalized === "HEALTHY" || normalized === "APPROVED" || normalized === "CONFIRMED") {
    badgeClass += "HEALTHY";
  } else {
    badgeClass += "HEALTHY";
  }

  return <span className={badgeClass}>{normalized}</span>;
};
