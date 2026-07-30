import React from "react";

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  if (!status) return <span className="badge-status HEALTHY">N/A</span>;

  let text = status.toUpperCase();
  if (text === "RAW_MATERIAL" || text === "RAW MATERIAL") text = "RM";
  if (text === "PACKAGING" || text === "PACKAGING MATERIAL") text = "PM";
  if (text === "FINISHED_GOOD" || text === "FINISHED GOOD") text = "FG";

  let badgeClass = "badge-status ";

  if (
    text === "CRITICAL" ||
    text === "REJECTED" ||
    text === "PRODUCTION BLOCKED" ||
    text === "PRODUCTION_BLOCKED" ||
    text === "REORDER REQUIRED"
  ) {
    badgeClass += "CRITICAL";
  } else if (
    text === "WARNING" ||
    text === "AT_RISK" ||
    text === "PENDING_APPROVAL" ||
    text === "LOW STOCK" ||
    text === "RM SHORTAGE" ||
    text === "RM_SHORTAGE" ||
    text === "PM SHORTAGE" ||
    text === "PM_SHORTAGE"
  ) {
    badgeClass += "WARNING";
  } else if (
    text === "HEALTHY" ||
    text === "APPROVED" ||
    text === "CONFIRMED" ||
    text === "READY TO PRODUCE" ||
    text === "READY_TO_PRODUCE"
  ) {
    badgeClass += "HEALTHY";
  } else {
    badgeClass += "HEALTHY";
  }

  let displayText = text;
  if (text === "AT_RISK") displayText = "At Risk";
  if (text === "PENDING_APPROVAL") displayText = "Pending Approval";
  if (text === "PRODUCTION_BLOCKED") displayText = "Production Blocked";
  if (text === "REORDER_REQUIRED") displayText = "Reorder Required";
  if (text === "READY_TO_PRODUCE") displayText = "Ready to Produce";
  if (text === "RM_SHORTAGE" || text === "RM SHORTAGE") displayText = "RM Shortage";
  if (text === "PM_SHORTAGE" || text === "PM SHORTAGE") displayText = "PM Shortage";

  return <span className={badgeClass}>{displayText}</span>;

};
