from __future__ import annotations

import enum
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.errors import AppError
from app.db.models.audit import AuditLog
from app.db.models.domain import (
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    PlanningReadinessScore,
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
    VendorMaterial,
)


class ReadinessStateEnum(enum.StrEnum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    BLOCKED = "BLOCKED"


class ConstraintSeverityEnum(enum.StrEnum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class ConstraintIssue(BaseModel):
    severity: ConstraintSeverityEnum
    category: str
    issue: str
    impact: str
    resolution_step: str


class PlanningReadinessReport(BaseModel):
    plant_code: str
    readiness_state: ReadinessStateEnum
    score: float
    missing_masters_count: int = 0
    missing_parameters_count: int = 0
    blocking_issues: list[ConstraintIssue] = Field(default_factory=list)
    warnings: list[ConstraintIssue] = Field(default_factory=list)
    info_messages: list[ConstraintIssue] = Field(default_factory=list)
    can_proceed_to_planning: bool = False
    is_acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanningReadinessEngine:
    """Gatekeeper engine evaluating dataset completeness, mandatory vs optional constraints,

    scoring, decision states, and planner acknowledgements.
    """

    def __init__(self, db: Session, user_id: int | None = None) -> None:
        self.db = db
        self.user_id = user_id

    def evaluate_readiness(self, plant_code: str) -> PlanningReadinessReport:
        p_code = plant_code.strip()
        plant = self.db.query(Plant).filter(Plant.code == p_code).first()

        blocking_issues: list[ConstraintIssue] = []
        warnings: list[ConstraintIssue] = []
        info_messages: list[ConstraintIssue] = []

        if not plant:
            blocking_issues.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.BLOCKING,
                    category="Plant Master",
                    issue=f"Plant code '{p_code}' does not exist in plant master",
                    impact="Planning calculations cannot be scoped to an invalid plant",
                    resolution_step="Upload Plant Master or create the plant in Plant Management.",
                )
            )
            report = PlanningReadinessReport(
                plant_code=p_code,
                readiness_state=ReadinessStateEnum.BLOCKED,
                score=0.0,
                missing_masters_count=1,
                blocking_issues=blocking_issues,
                can_proceed_to_planning=False,
            )
            self._persist_score(plant_id=None, report=report)
            return report

        # 1. Mandatory Data Check: Inventory Snapshots
        inv_count = (
            self.db.query(InventorySnapshot)
            .filter(InventorySnapshot.plant_id == plant.id)
            .count()
        )
        if inv_count == 0:
            blocking_issues.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.BLOCKING,
                    category="Stock Inventory Data",
                    issue="No stock inventory snapshot records found for plant",
                    impact="Available stock and days of inventory cannot be evaluated",
                    resolution_step="Upload current Stock inventory dataset (.xlsx/.csv) or trigger SAP inventory sync.",
                )
            )

        # 2. Mandatory Data Check: Consumption History
        cons_count = (
            self.db.query(ConsumptionHistory)
            .filter(ConsumptionHistory.plant_id == plant.id)
            .count()
        )
        if cons_count == 0:
            blocking_issues.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.BLOCKING,
                    category="Consumption Data",
                    issue="No consumption history records found for plant",
                    impact="Historical daily consumption trends and forecasting cannot be calculated",
                    resolution_step="Upload historical Consumption dataset (.xlsx/.csv) or trigger SAP consumption sync.",
                )
            )

        # 3. Optional Data Check: Purchase Orders
        po_count = (
            self.db.query(PurchaseOrder)
            .outerjoin(PurchaseOrderLine, PurchaseOrder.lines)
            .filter(or_(PurchaseOrder.plant_id == plant.id, PurchaseOrderLine.plant_id == plant.id))
            .count()
        )
        if po_count == 0:
            warnings.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.WARNING,
                    category="Purchase Orders",
                    issue="No open purchase order records found for plant",
                    impact="Incoming PO inventory buffer will be assumed as 0.0",
                    resolution_step="Upload open Purchase Orders dataset to account for incoming material buffers.",
                )
            )

        # 4. Material Parameter Check
        pms = (
            self.db.query(PlantMaterial)
            .filter(PlantMaterial.plant_id == plant.id)
            .all()
        )
        missing_params_count = 0
        for pm in pms:
            if pm.lead_time_1 is None or pm.safety_stock_1 is None or pm.trigger_1 is None:
                missing_params_count += 1

        if missing_params_count > 0:
            warnings.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.WARNING,
                    category="Material Parameters",
                    issue=f"{missing_params_count} material(s) lack RMPM parameters (Lead Time 1/2, Safety Stock 1/2)",
                    impact="Default fallback lead time (7.0 days) and safety stock buffers will be applied",
                    resolution_step="Upload Material Parameters dataset with RMPM LT-1/2 and SS-1/2 parameters.",
                )
            )

        # 5. Vendor Capacity Check
        vendor_materials = (
            self.db.query(VendorMaterial)
            .all()
        )
        missing_vendor_caps = [
            vm for vm in vendor_materials if vm.vendor and vm.vendor.capacity_per_day is None
        ]
        if missing_vendor_caps:
            warnings.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.WARNING,
                    category="Vendor Capacity",
                    issue=f"{len(missing_vendor_caps)} vendor(s) supplying plant lack daily capacity limits",
                    impact="Procurement allocation will not enforce maximum vendor daily order limits",
                    resolution_step="Upload Vendor Capacity dataset with daily supplier capacity numbers.",
                )
            )

        # 6. Informational Notices: Auto-generated Masters
        auto_masters = (
            self.db.query(AuditLog)
            .filter(AuditLog.action.like("AUTO_GENERATE_%"))
            .count()
        )
        if auto_masters > 0:
            info_messages.append(
                ConstraintIssue(
                    severity=ConstraintSeverityEnum.INFO,
                    category="Auto Master Generation",
                    issue=f"{auto_masters} master record(s) were auto-generated during ingestion",
                    impact="Master records were automatically derived from transactional uploads",
                    resolution_step="Review auto-generated masters in Master Data workspace if explicit details are needed.",
                )
            )

        # Calculate Readiness Score (0-100%)
        score = 100.0
        if blocking_issues:
            score -= len(blocking_issues) * 35.0
        if warnings:
            score -= len(warnings) * 10.0
        score = max(0.0, min(100.0, round(score, 1)))

        # Determine Decision State
        if blocking_issues:
            readiness_state = ReadinessStateEnum.BLOCKED
            can_proceed = False
        elif warnings:
            readiness_state = ReadinessStateEnum.READY_WITH_WARNINGS
            can_proceed = True
        else:
            readiness_state = ReadinessStateEnum.READY
            can_proceed = True

        # Check existing acknowledgement in audit log
        ack_log = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.action == "ACKNOWLEDGE_PLANNING_READINESS_WARNINGS",
                AuditLog.resource_id == p_code,
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        is_ack = False
        ack_by = None
        ack_at = None

        if ack_log:
            is_ack = True
            ack_by = ack_log.user_email or (f"User {ack_log.user_id}" if ack_log.user_id else "Planner")
            ack_at = ack_log.created_at

        report = PlanningReadinessReport(
            plant_code=p_code,
            readiness_state=readiness_state,
            score=score,
            missing_masters_count=1 if not plant else 0,
            missing_parameters_count=missing_params_count,
            blocking_issues=blocking_issues,
            warnings=warnings,
            info_messages=info_messages,
            can_proceed_to_planning=can_proceed,
            is_acknowledged=is_ack,
            acknowledged_by=ack_by,
            acknowledged_at=ack_at,
        )

        self._persist_score(plant_id=plant.id, report=report)

        # Log audit trail
        record_audit_event(
            self.db,
            user_id=self.user_id,
            action="EVALUATE_PLANNING_READINESS",
            resource_type="PlantReadiness",
            resource_id=p_code,
            details={
                "score": score,
                "readiness_state": readiness_state.value,
                "blocking_count": len(blocking_issues),
                "warnings_count": len(warnings),
            },
        )
        return report

    def acknowledge_warnings(self, plant_code: str, user_email: str | None = None) -> PlanningReadinessReport:
        report = self.evaluate_readiness(plant_code)

        if report.readiness_state == ReadinessStateEnum.BLOCKED:
            raise AppError(
                "CANNOT_ACKNOWLEDGE_BLOCKED_STATE",
                f"Cannot acknowledge planning readiness for plant '{plant_code}' because blocking issues exist. Resolve mandatory data constraints first.",
                400,
            )

        if not report.warnings:
            # Nothing to acknowledge, but already clean
            return report

        # Record acknowledgement in audit log
        ack_log = record_audit_event(
            self.db,
            user_id=self.user_id,
            user_email=user_email,
            action="ACKNOWLEDGE_PLANNING_READINESS_WARNINGS",
            resource_type="PlantReadiness",
            resource_id=plant_code,
            details={
                "acknowledged_warnings_count": len(report.warnings),
                "score": report.score,
                "warnings_summary": [w.issue for w in report.warnings],
            },
        )

        report.is_acknowledged = True
        report.acknowledged_by = user_email or (f"User {self.user_id}" if self.user_id else "Planner")
        report.acknowledged_at = ack_log.created_at
        return report

    def get_readiness_history(self, plant_code: str, limit: int = 20) -> list[dict[str, Any]]:
        plant = self.db.query(Plant).filter(Plant.code == plant_code).first()
        if not plant:
            return []

        records = (
            self.db.query(PlanningReadinessScore)
            .filter(PlanningReadinessScore.plant_id == plant.id)
            .order_by(PlanningReadinessScore.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": rec.id,
                "plant_code": plant_code,
                "score": rec.score,
                "missing_masters_count": rec.missing_masters_count,
                "missing_parameters_count": rec.missing_parameters_count,
                "details_json": rec.details_json,
                "created_at": rec.created_at.isoformat(),
            }
            for rec in records
        ]

    def _persist_score(self, plant_id: int | None, report: PlanningReadinessReport) -> None:
        if not plant_id:
            return
        score_rec = PlanningReadinessScore(
            plant_id=plant_id,
            score=report.score,
            missing_masters_count=report.missing_masters_count,
            missing_parameters_count=report.missing_parameters_count,
            details_json=json.dumps(
                {
                    "readiness_state": report.readiness_state.value,
                    "can_proceed": report.can_proceed_to_planning,
                    "blocking_count": len(report.blocking_issues),
                    "warnings_count": len(report.warnings),
                }
            ),
        )
        self.db.add(score_rec)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
