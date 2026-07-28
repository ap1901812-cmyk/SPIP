from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError

logger = logging.getLogger(__name__)

from app.db.models.domain import (
    BOM,
    InventorySnapshot,
    Material,
    MaterialTypeEnum,
    Plant,
    VendorMaterial,
)
from app.schemas.fg_planning import (
    AffectedFinishedGood,
    ComponentRequirement,
    FGPlanningRequest,
    FGPlanningResult,
    ProcurementRecommendation,
    RecommendationSummary,
    ShortageSummary,
)
from app.services.planning.availability import calculate_planning_availability
from app.services.planning.fg_engine import (
    compute_component_shortages,
    compute_fg_impact,
    compute_procurement_recommendations,
    explode_fg_demands,
)


class FGPlanningService:
    @staticmethod
    def _prepare_planning_context(
        db: Session, request: FGPlanningRequest
    ) -> tuple[
        list[dict[str, Any]],
        dict[int, dict[str, Any]],
        dict[int, list[dict[str, Any]]],
        dict[tuple[str, int], dict[str, Any]],
        dict[tuple[str, int], dict[str, Any]],
    ]:
        """Read-only database data loading for Planning Engine calculations."""
        # 1. Resolve plants
        plant_query = db.query(Plant)
        if request.plant_code:
            plant_query = plant_query.filter(Plant.code == request.plant_code)
        plants = plant_query.all()
        plant_map = {p.code: p for p in plants}

        # 2. Resolve demand items
        demand_items: list[dict[str, Any]] = []
        if request.demands:
            for item in request.demands:
                mat = db.query(Material).filter(Material.code == item.fg_code).first()
                if not mat:
                    raise AppError("NOT_FOUND", f"Finished Good with code '{item.fg_code}' not found.", 404)
                if item.plant_code not in plant_map:
                    p = db.query(Plant).filter(Plant.code == item.plant_code).first()
                    if not p:
                        raise AppError("NOT_FOUND", f"Plant with code '{item.plant_code}' not found.", 404)
                    plant_map[p.code] = p

                demand_items.append(
                    {
                        "fg_material_id": mat.id,
                        "fg_code": mat.code,
                        "plant_code": item.plant_code,
                        "demand_quantity": item.demand_quantity,
                    }
                )
        else:
            # Default: auto-discover FG materials across all available plants with default forecast demand of 100 units
            fg_materials = db.query(Material).filter(
                (Material.material_type == MaterialTypeEnum.FG.value)
                | (Material.material_type == "FINISHED_GOOD")
            ).all()
            for p in plants:
                for mat in fg_materials:
                    demand_items.append(
                        {
                            "fg_material_id": mat.id,
                            "fg_code": mat.code,
                            "plant_code": p.code,
                            "demand_quantity": 100.0,
                        }
                    )

        # 3. Load all material info map
        all_materials = db.query(Material).all()
        material_info_map = {
            m.id: {
                "id": m.id,
                "code": m.code,
                "description": m.description,
                "material_type": MaterialTypeEnum.normalize(m.material_type),
                "base_uom": m.base_uom,
            }
            for m in all_materials
        }

        # 4. Load BOM map
        all_boms = db.query(BOM).options(joinedload(BOM.component_material)).filter(BOM.is_active == True).all()
        bom_map: dict[int, list[dict[str, Any]]] = {}
        for b in all_boms:
            if b.fg_material_id not in bom_map:
                bom_map[b.fg_material_id] = []
            bom_map[b.fg_material_id].append(
                {
                    "fg_material_id": b.fg_material_id,
                    "component_material_id": b.component_material_id,
                    "component_code": b.component_material.code if b.component_material else "",
                    "required_quantity": b.required_quantity,
                    "unit_of_measure": b.unit_of_measure,
                }
            )

        # 5. Load Availability map using existing calculate_planning_availability service
        availability_map: dict[tuple[str, int], dict[str, Any]] = {}
        for p_code, plant_obj in plant_map.items():
            for m_id, mat_info in material_info_map.items():
                try:
                    avail_res = calculate_planning_availability(db, plant_obj.id, m_id)
                    availability_map[(p_code, m_id)] = {
                        "usable_physical_stock": avail_res.usable_physical_stock,
                        "planning_availability": avail_res.planning_availability,
                    }
                except Exception:
                    availability_map[(p_code, m_id)] = {
                        "usable_physical_stock": 0.0,
                        "planning_availability": 0.0,
                    }

        # 6. Load VendorMaterial map for procurement recommendations
        vms = db.query(VendorMaterial).options(joinedload(VendorMaterial.vendor), joinedload(VendorMaterial.plant)).all()
        vendor_map: dict[tuple[str, int], dict[str, Any]] = {}
        for vm in vms:
            if vm.plant and vm.is_primary:
                vendor_map[(vm.plant.code, vm.material_id)] = {
                    "vendor_code": vm.vendor.code if vm.vendor else None,
                    "vendor_name": vm.vendor.name if vm.vendor else None,
                    "vendor_lead_time_days": vm.vendor_lead_time_days or 7.0,
                    "min_order_qty": vm.min_order_qty or 0.0,
                }

        return demand_items, material_info_map, bom_map, availability_map, vendor_map

    @staticmethod
    def run_planning(db: Session, request: FGPlanningRequest) -> FGPlanningResult:
        """Stateless Orchestration:
        Loads context from DB read-only, invokes fg_engine pure calculations, and returns structured result.
        """
        demand_items, material_info_map, bom_map, availability_map, vendor_map = (
            FGPlanningService._prepare_planning_context(db, request)
        )

        # 1. Explode demands
        gross_requirements, _ = explode_fg_demands(demand_items, bom_map)

        # 2. Compute component shortages
        shortages_raw = compute_component_shortages(
            gross_requirements, material_info_map, availability_map
        )
        component_reqs = [ComponentRequirement.model_validate(s) for s in shortages_raw]

        # 3. Compute procurement recommendations
        recommendations_raw = compute_procurement_recommendations(shortages_raw, vendor_map)
        procurement_recs = [ProcurementRecommendation.model_validate(r) for r in recommendations_raw]

        # 4. Compute FG production impact
        shortage_qty_map = {(s["plant_code"], s["component_material_id"]): s["shortage_quantity"] for s in shortages_raw}
        avail_qty_map = {key: val["planning_availability"] for key, val in availability_map.items()}

        impacts_raw = compute_fg_impact(
            demand_items, material_info_map, bom_map, shortage_qty_map, avail_qty_map
        )
        affected_fgs = [AffectedFinishedGood.model_validate(i) for i in impacts_raw]

        critical_count = sum(1 for c in component_reqs if c.criticality_status == "CRITICAL")
        warning_count = sum(1 for c in component_reqs if c.criticality_status == "WARNING")

        summary = {
            "total_demand_items_evaluated": len(demand_items),
            "total_components_evaluated": len(component_reqs),
            "critical_shortages_count": critical_count,
            "warning_shortages_count": warning_count,
            "procurement_recommendations_count": len(procurement_recs),
            "affected_finished_goods_count": sum(1 for a in affected_fgs if a.risk_status != "HEALTHY"),
        }

        logger.info(
            "Executed FG Planning Engine run: %d demand items evaluated, %d shortages (%d critical), %d procurement recommendations generated.",
            summary["total_demand_items_evaluated"],
            summary["total_components_evaluated"],
            critical_count,
            summary["procurement_recommendations_count"],
        )

        return FGPlanningResult(
            summary=summary,
            component_requirements=component_reqs,
            procurement_recommendations=procurement_recs,
            affected_finished_goods=affected_fgs,
        )

    @staticmethod
    def get_shortage_summary(db: Session, plant_code: str | None = None) -> ShortageSummary:
        req = FGPlanningRequest(plant_code=plant_code)
        result = FGPlanningService.run_planning(db, req)

        shortages = [c for c in result.component_requirements if c.shortage_quantity > 0 or c.criticality_status == "CRITICAL"]
        critical_count = sum(1 for c in shortages if c.criticality_status == "CRITICAL")

        return ShortageSummary(
            total_shortages_count=len(shortages),
            critical_shortages_count=critical_count,
            shortages=shortages,
        )

    @staticmethod
    def get_recommendation_summary(db: Session, plant_code: str | None = None) -> RecommendationSummary:
        req = FGPlanningRequest(plant_code=plant_code)
        result = FGPlanningService.run_planning(db, req)

        recs = result.procurement_recommendations
        return RecommendationSummary(
            total_recommendations_count=len(recs),
            recommendations=recs,
        )
