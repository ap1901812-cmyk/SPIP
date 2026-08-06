from __future__ import annotations

import math
from typing import Any


def explode_fg_demands(
    demand_items: list[dict[str, Any]],
    bom_map: dict[int, list[dict[str, Any]]],
) -> tuple[dict[tuple[str, int], float], dict[tuple[str, int], list[tuple[int, float]]]]:
    """Stateless BOM Explosion:
    Calculates gross requirements per (plant_code, component_material_id)
    and tracks component usage per FG item.
    """
    gross_requirements: dict[tuple[str, int], float] = {}
    component_usages: dict[tuple[str, int], list[tuple[int, float]]] = {}

    for item in demand_items:
        plant_code = item["plant_code"]
        fg_id = item["fg_material_id"]
        fg_qty = item["demand_quantity"]

        boms = bom_map.get(fg_id, [])
        for bom in boms:
            comp_id = bom["component_material_id"]
            req_qty = bom["required_quantity"] * fg_qty

            key = (plant_code, comp_id)
            gross_requirements[key] = gross_requirements.get(key, 0.0) + req_qty

            if key not in component_usages:
                component_usages[key] = []
            component_usages[key].append((fg_id, req_qty))

    return gross_requirements, component_usages


def compute_component_shortages(
    gross_requirements: dict[tuple[str, int], float],
    material_info_map: dict[int, dict[str, Any]],
    availability_map: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stateless Shortage & Criticality Computation:
    Calculates net shortages and explainable reasons for each component requirement.
    """
    results: list[dict[str, Any]] = []

    for (plant_code, comp_id), gross_req in gross_requirements.items():
        mat = material_info_map.get(comp_id, {})
        avail_info = availability_map.get((plant_code, comp_id), {})

        physical_stock = float(avail_info.get("usable_physical_stock", 0.0))
        avail = float(avail_info.get("planning_availability", 0.0))
        shortage = max(0.0, round(gross_req - avail, 4))

        if shortage > 0:
            status = "CRITICAL"
            explanation = (
                f"{mat.get('code', 'Component')} has a net shortage of {shortage:.1f} {mat.get('base_uom', 'units')} "
                f"at {plant_code}. Gross requirement ({gross_req:.1f} {mat.get('base_uom', 'units')}) exceeds "
                f"planning availability ({avail:.1f} {mat.get('base_uom', 'units')})."
            )
        elif avail < gross_req * 1.1:
            status = "WARNING"
            explanation = (
                f"{mat.get('code', 'Component')} planning availability ({avail:.1f} {mat.get('base_uom', 'units')}) "
                f"at {plant_code} is near gross requirement ({gross_req:.1f} {mat.get('base_uom', 'units')})."
            )
        else:
            status = "HEALTHY"
            explanation = (
                f"{mat.get('code', 'Component')} has sufficient availability ({avail:.1f} {mat.get('base_uom', 'units')}) "
                f"for gross requirement ({gross_req:.1f} {mat.get('base_uom', 'units')}) at {plant_code}."
            )

        results.append(
            {
                "plant_code": plant_code,
                "component_material_id": comp_id,
                "component_code": mat.get("code", f"MAT-{comp_id}"),
                "component_description": mat.get("description", "Material"),
                "component_type": mat.get("material_type", "RM"),
                "base_uom": mat.get("base_uom", "KG"),
                "gross_requirement": round(gross_req, 4),
                "usable_physical_stock": round(physical_stock, 4),
                "planning_availability": round(avail, 4),
                "shortage_quantity": shortage,
                "criticality_status": status,
                "explanation": explanation,
            }
        )

    return results


def compute_procurement_recommendations(
    shortages: list[dict[str, Any]],
    vendor_map: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stateless Procurement Recommendation Computation:
    Calculates recommended purchase order quantities honoring MOQ and vendor lead times.
    """
    recommendations: list[dict[str, Any]] = []

    for item in shortages:
        if item["shortage_quantity"] <= 0:
            continue

        plant_code = item["plant_code"]
        comp_id = item["component_material_id"]
        shortage = item["shortage_quantity"]
        uom = item["base_uom"]

        vend = vendor_map.get(comp_id, {})
        min_qty = float(vend.get("min_order_qty") or 0.0)
        lead_time = float(vend.get("vendor_lead_time_days") or 7.0)

        recommended_qty = max(shortage, min_qty)
        if min_qty > 0 and recommended_qty > shortage:
            moq_note = f" (adjusted from shortage of {shortage:.1f} {uom} to meet Minimum Order Qty of {min_qty:.1f} {uom})"
        else:
            moq_note = ""

        vend_name = vend.get("vendor_name", "Primary Vendor")
        explanation = (
            f"Recommended to procure {recommended_qty:.1f} {uom} of {item['component_code']} from {vend_name} "
            f"to resolve {shortage:.1f} {uom} shortage at {plant_code}{moq_note}. Expected lead time: {lead_time:.0f} days."
        )

        recommendations.append(
            {
                "plant_code": plant_code,
                "component_code": item["component_code"],
                "component_description": item["component_description"],
                "shortage_quantity": shortage,
                "recommended_order_qty": round(recommended_qty, 4),
                "uom": uom,
                "vendor_code": vend.get("vendor_code"),
                "vendor_name": vend.get("vendor_name"),
                "lead_time_days": lead_time,
                "min_order_qty": min_qty,
                "explanation": explanation,
            }
        )

    return recommendations


def compute_fg_impact(
    demand_items: list[dict[str, Any]],
    fg_info_map: dict[int, dict[str, Any]],
    bom_map: dict[int, list[dict[str, Any]]],
    shortage_map: dict[tuple[str, int], float],
    availability_map: dict[tuple[str, int], float],
) -> list[dict[str, Any]]:
    """Stateless FG Impact & Feasibility Calculation:
    Calculates maximum feasible production per FG based on bottleneck component availability.
    """
    impacts: list[dict[str, Any]] = []

    for item in demand_items:
        plant_code = item["plant_code"]
        fg_id = item["fg_material_id"]
        demand_qty = item["demand_quantity"]
        fg_info = fg_info_map.get(fg_id, {})

        boms = bom_map.get(fg_id, [])
        feasible_qty = demand_qty
        bottleneck_code: str | None = None

        for bom in boms:
            comp_id = bom["component_material_id"]
            req_per_unit = bom["required_quantity"]
            if req_per_unit <= 0:
                continue

            comp_code = bom.get("component_code", f"MAT-{comp_id}")
            comp_avail = availability_map.get((plant_code, comp_id), 0.0)

            possible_fg = comp_avail / req_per_unit
            if possible_fg < feasible_qty:
                feasible_qty = possible_fg
                bottleneck_code = comp_code

        feasible_qty = max(0.0, round(feasible_qty, 4))
        unmet_demand = max(0.0, round(demand_qty - feasible_qty, 4))

        if unmet_demand > 0:
            status = "CRITICAL" if feasible_qty == 0 else "AT_RISK"
            explanation = (
                f"{fg_info.get('code', 'FG')} production is {status} at {plant_code}. "
                f"Demand is {demand_qty:.1f} units, but bottleneck component '{bottleneck_code}' "
                f"limits feasible production to {feasible_qty:.1f} units (unmet demand: {unmet_demand:.1f} units)."
            )
        else:
            status = "HEALTHY"
            explanation = (
                f"{fg_info.get('code', 'FG')} has full component availability at {plant_code} "
                f"to support forecast demand of {demand_qty:.1f} units."
            )

        impacts.append(
            {
                "plant_code": plant_code,
                "fg_code": fg_info.get("code", f"FG-{fg_id}"),
                "fg_description": fg_info.get("description", "Finished Good"),
                "forecast_demand": demand_qty,
                "feasible_production": feasible_qty,
                "unmet_demand": unmet_demand,
                "bottleneck_component_code": bottleneck_code,
                "risk_status": status,
                "explanation": explanation,
            }
        )

    return impacts
