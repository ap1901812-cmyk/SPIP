from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import Material, Plant, PlantMaterial, SimulationRun
from app.services.planning.orchestrator import execute_full_planning_pipeline


class ScenarioOverrides(BaseModel):
    inventory_override_qty: float | None = Field(None, description="Simulated stock level override")
    demand_multiplier: float = Field(1.0, ge=0.1, le=10.0, description="Demand multiplier (e.g. 1.25 = +25%)")
    lead_time_override_days: float | None = Field(None, description="Simulated supplier lead time in days")
    safety_stock_multiplier: float = Field(1.0, ge=0.1, le=5.0, description="Safety stock multiplier")
    vendor_capacity_multiplier: float = Field(1.0, ge=0.1, le=5.0, description="Vendor capacity multiplier")


class SimulationRunItem(BaseModel):
    id: int
    user_id: int
    user_email: str | None = None
    scenario_name: str
    plant_code: str
    material_code: str | None = None
    input_params: dict[str, Any]
    results: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


def run_what_if_simulation(
    db: Session,
    user_id: int,
    scenario_name: str,
    plant_code: str,
    material_code: str | None = None,
    overrides: ScenarioOverrides | None = None,
) -> SimulationRunItem:
    """Executes an isolated What-If scenario simulation without modifying production data."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise AppError("PLANT_NOT_FOUND", f"Plant with code '{plant_code}' not found.", 404)

    opts = overrides or ScenarioOverrides()

    # Base pipeline execution
    base_res = execute_full_planning_pipeline(
        db=db, plant_code=plant_code, material_code=material_code, horizon_days=15
    )

    sim_results = json.loads(json.dumps(base_res.intermediate_results, default=str))

    # Apply Simulation Overrides in-memory
    if opts.inventory_override_qty is not None:
        if "inventory_intelligence" in sim_results:
            sim_results["inventory_intelligence"]["usable_physical_stock"] = opts.inventory_override_qty
            sim_results["inventory_intelligence"]["planning_available_inventory"] = (
                opts.inventory_override_qty + sim_results["inventory_intelligence"].get("incoming_po_quantity", 0.0)
            )

    if opts.demand_multiplier != 1.0:
        if "consumption_intelligence" in sim_results:
            base_dem = sim_results["consumption_intelligence"].get("average_daily_demand", 0.0)
            sim_results["consumption_intelligence"]["average_daily_demand"] = round(base_dem * opts.demand_multiplier, 2)

        if "requirement_resolution" in sim_results:
            base_req = sim_results["requirement_resolution"].get("final_planning_requirement", 0.0)
            sim_results["requirement_resolution"]["final_planning_requirement"] = round(base_req * opts.demand_multiplier, 2)

    if opts.lead_time_override_days is not None:
        if "rmpm_statistical_planning" in sim_results:
            sim_results["rmpm_statistical_planning"]["lead_time_1"] = opts.lead_time_override_days

    if opts.safety_stock_multiplier != 1.0:
        if "rmpm_statistical_planning" in sim_results:
            ss1 = sim_results["rmpm_statistical_planning"].get("safety_stock_1", 0.0)
            sim_results["rmpm_statistical_planning"]["safety_stock_1"] = round(ss1 * opts.safety_stock_multiplier, 2)

    # Calculate Simulated Impact
    sim_inv = sim_results.get("inventory_intelligence", {})
    sim_avail = sim_inv.get("planning_available_inventory", 0.0)

    sim_req = sim_results.get("requirement_resolution", {})
    sim_daily_req = sim_req.get("final_planning_requirement", 0.0)

    sim_rmpm = sim_results.get("rmpm_statistical_planning", {})
    sim_ss1 = sim_rmpm.get("safety_stock_1", 0.0)

    sim_horizon_demand = sim_daily_req * 15.0
    sim_net_deficit = max(0.0, sim_horizon_demand + sim_ss1 - sim_avail)

    sim_results["simulation_impact_summary"] = {
        "scenario_name": scenario_name,
        "simulated_available_inventory": round(sim_avail, 2),
        "simulated_daily_demand": round(sim_daily_req, 2),
        "simulated_safety_stock_target": round(sim_ss1, 2),
        "simulated_15_day_horizon_requirement": round(sim_horizon_demand, 2),
        "simulated_net_procurement_deficit": round(sim_net_deficit, 2),
        "simulated_priority": "CRITICAL" if sim_avail <= sim_ss1 else ("HIGH" if sim_net_deficit > 0 else "LOW"),
    }

    input_payload = {
        "scenario_name": scenario_name,
        "plant_code": plant_code,
        "material_code": material_code,
        "overrides": opts.model_dump(),
    }

    sim_record = SimulationRun(
        user_id=user_id,
        scenario_name=scenario_name,
        input_params_json=json.dumps(input_payload, default=str),
        results_json=json.dumps(sim_results, default=str),
    )
    db.add(sim_record)
    db.commit()
    db.refresh(sim_record)

    return SimulationRunItem(
        id=sim_record.id,
        user_id=user_id,
        user_email=sim_record.user.email if sim_record.user else None,
        scenario_name=scenario_name,
        plant_code=plant_code,
        material_code=material_code,
        input_params=input_payload,
        results=sim_results,
    )


def get_simulation_history(db: Session, user_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = db.query(SimulationRun)
    if user_id:
        query = query.filter(SimulationRun.user_id == user_id)

    records = query.order_by(SimulationRun.id.desc()).limit(limit).all()
    output = []
    for r in records:
        in_params = json.loads(r.input_params_json) if r.input_params_json else {}
        output.append(
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_email": r.user.email if r.user else None,
                "scenario_name": r.scenario_name,
                "plant_code": in_params.get("plant_code"),
                "material_code": in_params.get("material_code"),
                "input_params": in_params,
            }
        )
    return output


def get_simulation_detail(db: Session, simulation_id: int) -> dict[str, Any]:
    record = db.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
    if not record:
        raise AppError("SIMULATION_NOT_FOUND", f"Simulation with ID {simulation_id} not found.", 404)

    in_params = json.loads(record.input_params_json) if record.input_params_json else {}
    res_data = json.loads(record.results_json) if record.results_json else {}

    return {
        "id": record.id,
        "user_id": record.user_id,
        "user_email": record.user.email if record.user else None,
        "scenario_name": record.scenario_name,
        "input_params": in_params,
        "results": res_data,
    }
