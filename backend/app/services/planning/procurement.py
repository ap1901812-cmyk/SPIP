from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.errors import AppError
from app.db.models.domain import (
    Material,
    MaterialTypeEnum,
    Plant,
    PlantMaterial,
    ProcurementRecommendation,
    Vendor,
    VendorMaterial,
)
from app.services.planning.orchestrator import execute_full_planning_pipeline


class RecommendationExplainability(BaseModel):
    requirement_reason: str
    triggering_module: str
    applied_constraints: dict[str, Any] = Field(default_factory=dict)
    quantity_justification: str
    date_justification: str


class ProcurementRecommendationItem(BaseModel):
    id: int | None = None
    plant_code: str
    material_code: str
    material_description: str
    material_type: str
    recommended_qty: float
    recommended_vendor_id: int | None = None
    recommended_vendor_code: str | None = None
    recommended_vendor_name: str | None = None
    recommended_procurement_date: date
    dispatch_date: date
    expected_arrival_date: date
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    planning_mode: str  # PROACTIVE, REACTIVE
    status: str  # RECOMMENDED, ACCEPTED, REJECTED, EDITS_SUBMITTED
    reason: str
    explanation: RecommendationExplainability
    created_at: datetime | None = None


class ProcurementRecommendationSummary(BaseModel):
    plant_code: str
    total_recommendations_generated: int
    proactive_count: int
    reactive_count: int
    critical_count: int
    high_priority_count: int
    recommendations: list[ProcurementRecommendationItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


def generate_procurement_recommendations(
    db: Session,
    plant_code: str,
    material_code: str | None = None,
    horizon_days: int = 15,
    planning_mode: str = "PROACTIVE",
    user_id: int | None = None,
) -> ProcurementRecommendationSummary:
    """Generates actionable procurement recommendations from Central Planning Orchestrator outputs.

    Does NOT create Purchase Orders or invoke Vendor Allocation.
    Consumes outputs from statistical planning, inventory, requirement resolution, and production readiness.
    """
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise AppError("PLANT_NOT_FOUND", f"Plant with code '{plant_code}' not found.", 440)

    # Execute Central Orchestrator pipeline
    pipeline_res = execute_full_planning_pipeline(
        db=db, plant_code=plant_code, material_code=material_code, horizon_days=horizon_days
    )

    if pipeline_res.execution_metadata.status == "BLOCKED":
        raise AppError(
            "PLANNING_READINESS_BLOCKED",
            f"Cannot generate procurement recommendations: {pipeline_res.execution_metadata.failure_reason}",
            400,
        )

    # Determine materials to evaluate
    if material_code:
        materials_query = db.query(Material).filter(Material.code == material_code).all()
    else:
        materials_query = (
            db.query(Material)
            .join(PlantMaterial, PlantMaterial.material_id == Material.id)
            .filter(PlantMaterial.plant_id == plant.id)
            .all()
        )

    today = date.today()
    recommendations_list: list[ProcurementRecommendationItem] = []

    proactive_cnt = 0
    reactive_cnt = 0
    critical_cnt = 0
    high_cnt = 0

    for mat in materials_query:
        # Recommendations apply only to purchasable Raw Materials & Packaging Materials
        m_type = MaterialTypeEnum.normalize(mat.material_type)
        if m_type not in (MaterialTypeEnum.RM.value, MaterialTypeEnum.PM.value):
            continue

        pm = (
            db.query(PlantMaterial)
            .filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == mat.id)
            .first()
        )

        # Primary Vendor & Lead Time Lookup
        primary_vm = (
            db.query(VendorMaterial)
            .filter(
                VendorMaterial.plant_id == plant.id,
                VendorMaterial.material_id == mat.id,
                VendorMaterial.is_primary == True,
            )
            .first()
        )
        if not primary_vm:
            primary_vm = (
                db.query(VendorMaterial)
                .filter(VendorMaterial.plant_id == plant.id, VendorMaterial.material_id == mat.id)
                .first()
            )

        vendor = primary_vm.vendor if primary_vm else None
        lead_time_days = (
            primary_vm.vendor_lead_time_days
            if primary_vm and primary_vm.vendor_lead_time_days is not None
            else (pm.lead_time_1 if pm and pm.lead_time_1 is not None else (pm.lead_time_days if pm and pm.lead_time_days is not None else 7.0))
        )

        # Extract Orchestrator Planning Outputs
        mod_results = pipeline_res.intermediate_results
        inv_data = mod_results.get("inventory_intelligence", {})
        usable_stock = inv_data.get("usable_physical_stock", 0.0)
        incoming_po = inv_data.get("incoming_po_quantity", 0.0)
        net_available = inv_data.get("planning_available_inventory", usable_stock + incoming_po)

        req_data = mod_results.get("requirement_resolution", {})
        daily_req = req_data.get("final_planning_requirement", 0.0)
        req_source = req_data.get("requirement_source", "HISTORICAL_AVERAGE")

        rmpm_data = mod_results.get("rmpm_statistical_planning", {})
        ss_1 = rmpm_data.get("safety_stock_1", pm.safety_stock_1 if pm and pm.safety_stock_1 else (pm.safety_stock if pm else 0.0))
        ss_2 = rmpm_data.get("safety_stock_2", pm.safety_stock_2 if pm and pm.safety_stock_2 else 0.0)
        trig_1 = rmpm_data.get("trigger_1", net_available - (daily_req * lead_time_days) - ss_1)

        # Total Requirement over horizon
        total_horizon_req = daily_req * horizon_days
        buffer_target = ss_1 if ss_1 > 0 else (pm.safety_stock if pm else 0.0)

        # Evaluate Net Deficit & Procurement Need
        gross_needed = total_horizon_req + buffer_target
        net_deficit = max(0.0, gross_needed - net_available)

        # Determine Priority & Mode
        if net_available <= buffer_target or net_available <= 0:
            priority = "CRITICAL"
            mode = "REACTIVE"
            req_reason = f"Inventory level ({net_available:.1f} {mat.base_uom}) is at or below Safety Stock buffer ({buffer_target:.1f} {mat.base_uom})."
        elif net_available <= trig_1:
            priority = "HIGH"
            mode = planning_mode.upper() if planning_mode else "PROACTIVE"
            req_reason = f"Inventory level ({net_available:.1f} {mat.base_uom}) breached Trigger-1 threshold ({trig_1:.1f} {mat.base_uom})."
        elif net_deficit > 0:
            priority = "MEDIUM"
            mode = planning_mode.upper() if planning_mode else "PROACTIVE"
            req_reason = f"Planning horizon demand ({total_horizon_req:.1f} {mat.base_uom}) exceeds net available inventory ({net_available:.1f} {mat.base_uom})."
        else:
            # Stock is healthy; check if reactive explicitly requested
            if planning_mode.upper() == "REACTIVE":
                priority = "LOW"
                mode = "REACTIVE"
                req_reason = f"Reactive procurement analysis requested for material '{mat.code}'."
                net_deficit = round(daily_req * 7.0, 2)  # 7-day replenishment buffer for reactive inquiry
            else:
                # No recommendation needed
                continue

        # Adjust Quantity for Constraints (Minimum Order Qty / Storage Limit)
        min_order_qty = primary_vm.min_order_qty if primary_vm and primary_vm.min_order_qty else 0.0
        final_rec_qty = max(net_deficit, min_order_qty)
        if final_rec_qty <= 0:
            continue

        # Storage Limit Constraint Check
        storage_cap = mat.storage_capacity_limit
        capping_note = ""
        if storage_cap and storage_cap > 0:
            if usable_stock + final_rec_qty > storage_cap:
                max_allowed = max(0.0, storage_cap - usable_stock)
                if max_allowed < final_rec_qty:
                    capping_note = f" (Capped from {final_rec_qty:.1f} due to Plant Storage Limit of {storage_cap:.1f} {mat.base_uom})"
                    final_rec_qty = max_allowed

        # Vendor Capacity Note
        vendor_cap_note = f"{vendor.capacity_per_day:.1f}/day" if vendor and vendor.capacity_per_day else "Unconstrained"

        # Date Calculation
        # Expected Arrival: when material is required in plant
        days_until_buffer_breach = int(net_available / daily_req) if daily_req > 0 else 7
        arrival_lead = min(horizon_days, max(1, days_until_buffer_breach))
        expected_arrival = today + timedelta(days=arrival_lead)

        procurement_date = max(today, expected_arrival - timedelta(days=int(lead_time_days)))
        dispatch_offset = max(1, int(lead_time_days) - 2)
        dispatch_date = procurement_date + timedelta(days=dispatch_offset)

        # Build Explainability Payload
        explainability = RecommendationExplainability(
            requirement_reason=req_reason,
            triggering_module=f"Requirement Resolution ({req_source}) & Statistical Planning",
            applied_constraints={
                "lead_time_days": lead_time_days,
                "safety_stock_1_buffer": ss_1,
                "safety_stock_2_buffer": ss_2,
                "trigger_1_level": trig_1,
                "usable_physical_stock": usable_stock,
                "incoming_po_quantity": incoming_po,
                "net_available_inventory": net_available,
                "plant_storage_capacity_limit": storage_cap or "Unlimited",
                "vendor_daily_capacity": vendor_cap_note,
                "minimum_order_quantity": min_order_qty,
            },
            quantity_justification=(
                f"Calculated gross requirement of {gross_needed:.1f} {mat.base_uom} minus net available stock "
                f"({net_available:.1f} {mat.base_uom}) yielded net deficit of {net_deficit:.1f} {mat.base_uom}."
                f"{capping_note}"
            ),
            date_justification=(
                f"Expected arrival date ({expected_arrival.isoformat()}) set by inventory breach window. "
                f"Recommended procurement date ({procurement_date.isoformat()}) derived by subtracting {lead_time_days:.1f} lead time days."
            ),
        )

        # Persist to Database
        rec_model = ProcurementRecommendation(
            plant_id=plant.id,
            material_id=mat.id,
            recommended_qty=round(final_rec_qty, 2),
            recommended_vendor_id=vendor.id if vendor else None,
            recommended_procurement_date=procurement_date,
            dispatch_date=dispatch_date,
            expected_arrival_date=expected_arrival,
            priority=priority,
            planning_mode=mode,
            status="RECOMMENDED",
            reason=req_reason + capping_note,
            explanation_json=explainability.model_dump_json(),
        )
        db.add(rec_model)
        db.commit()
        db.refresh(rec_model)

        item = ProcurementRecommendationItem(
            id=rec_model.id,
            plant_code=plant.code,
            material_code=mat.code,
            material_description=mat.description,
            material_type=m_type,
            recommended_qty=round(final_rec_qty, 2),
            recommended_vendor_id=vendor.id if vendor else None,
            recommended_vendor_code=vendor.code if vendor else None,
            recommended_vendor_name=vendor.name if vendor else None,
            recommended_procurement_date=procurement_date,
            dispatch_date=dispatch_date,
            expected_arrival_date=expected_arrival,
            priority=priority,
            planning_mode=mode,
            status="RECOMMENDED",
            reason=req_reason + capping_note,
            explanation=explainability,
            created_at=rec_model.created_at,
        )
        recommendations_list.append(item)

        if mode == "PROACTIVE":
            proactive_cnt += 1
        else:
            reactive_cnt += 1

        if priority == "CRITICAL":
            critical_cnt += 1
        elif priority == "HIGH":
            high_cnt += 1

    # Record Audit Event
    record_audit_event(
        db,
        user_id=user_id,
        action="GENERATE_PROCUREMENT_RECOMMENDATIONS",
        resource_type="PlantProcurement",
        resource_id=plant_code,
        details={
            "total_generated": len(recommendations_list),
            "proactive_count": proactive_cnt,
            "reactive_count": reactive_cnt,
            "critical_count": critical_cnt,
        },
    )

    return ProcurementRecommendationSummary(
        plant_code=plant.code,
        total_recommendations_generated=len(recommendations_list),
        proactive_count=proactive_cnt,
        reactive_count=reactive_cnt,
        critical_count=critical_cnt,
        high_priority_count=high_cnt,
        recommendations=recommendations_list,
    )


def refresh_procurement_recommendations(
    db: Session, plant_code: str, user_id: int | None = None
) -> ProcurementRecommendationSummary:
    """Dynamic Recommendation Refresh handler triggered automatically on SAP or file ingestion events."""
    return generate_procurement_recommendations(
        db=db, plant_code=plant_code, planning_mode="PROACTIVE", user_id=user_id
    )


def get_procurement_recommendation_history(
    db: Session, plant_code: str, material_code: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    """Retrieves stored procurement recommendations history for a plant."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        return []

    query = (
        db.query(ProcurementRecommendation)
        .filter(ProcurementRecommendation.plant_id == plant.id)
    )
    if material_code:
        mat = db.query(Material).filter(Material.code == material_code).first()
        if mat:
            query = query.filter(ProcurementRecommendation.material_id == mat.id)

    records = query.order_by(ProcurementRecommendation.created_at.desc()).limit(limit).all()

    output = []
    for r in records:
        exp_dict = json.loads(r.explanation_json) if r.explanation_json else {}
        output.append(
            {
                "id": r.id,
                "plant_code": plant_code,
                "material_code": r.material.code if r.material else None,
                "material_description": r.material.description if r.material else None,
                "material_type": MaterialTypeEnum.normalize(r.material.material_type) if r.material else "RM",
                "recommended_qty": r.recommended_qty,
                "recommended_vendor_id": r.recommended_vendor_id,
                "recommended_vendor_code": r.recommended_vendor.code if r.recommended_vendor else None,
                "recommended_vendor_name": r.recommended_vendor.name if r.recommended_vendor else None,
                "recommended_procurement_date": r.recommended_procurement_date.isoformat() if r.recommended_procurement_date else None,
                "dispatch_date": r.dispatch_date.isoformat() if r.dispatch_date else None,
                "expected_arrival_date": r.expected_arrival_date.isoformat() if r.expected_arrival_date else None,
                "priority": r.priority,
                "planning_mode": r.planning_mode,
                "status": r.status,
                "reason": r.reason,
                "explanation": exp_dict,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return output


def get_procurement_recommendation_by_id(
    db: Session, recommendation_id: int
) -> dict[str, Any]:
    """Retrieves full details and explainability for a specific recommendation."""
    rec = (
        db.query(ProcurementRecommendation)
        .filter(ProcurementRecommendation.id == recommendation_id)
        .first()
    )
    if not rec:
        raise AppError(
            "RECOMMENDATION_NOT_FOUND",
            f"Procurement recommendation with ID {recommendation_id} not found.",
            404,
        )

    exp_dict = json.loads(rec.explanation_json) if rec.explanation_json else {}
    return {
        "id": rec.id,
        "plant_code": rec.plant.code if rec.plant else None,
        "material_code": rec.material.code if rec.material else None,
        "material_description": rec.material.description if rec.material else None,
        "material_type": MaterialTypeEnum.normalize(rec.material.material_type) if rec.material else "RM",
        "recommended_qty": rec.recommended_qty,
        "recommended_vendor_id": rec.recommended_vendor_id,
        "recommended_vendor_code": rec.recommended_vendor.code if rec.recommended_vendor else None,
        "recommended_vendor_name": rec.recommended_vendor.name if rec.recommended_vendor else None,
        "recommended_procurement_date": rec.recommended_procurement_date.isoformat() if rec.recommended_procurement_date else None,
        "dispatch_date": rec.dispatch_date.isoformat() if rec.dispatch_date else None,
        "expected_arrival_date": rec.expected_arrival_date.isoformat() if rec.expected_arrival_date else None,
        "priority": rec.priority,
        "planning_mode": rec.planning_mode,
        "status": rec.status,
        "reason": rec.reason,
        "explanation": exp_dict,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }
