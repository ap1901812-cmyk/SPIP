from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FGDemandItem(BaseModel):
    fg_code: str = Field(..., max_length=50)
    plant_code: str = Field(..., max_length=20)
    demand_quantity: float = Field(..., gt=0.0)


class FGPlanningRequest(BaseModel):
    demands: list[FGDemandItem] = []
    plant_code: str | None = None


class ComponentRequirement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plant_code: str
    component_code: str
    component_description: str
    component_type: str
    base_uom: str
    gross_requirement: float
    usable_physical_stock: float
    planning_availability: float
    shortage_quantity: float
    criticality_status: str
    explanation: str


class ProcurementRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plant_code: str
    component_code: str
    component_description: str
    shortage_quantity: float
    recommended_order_qty: float
    uom: str
    vendor_code: str | None = None
    vendor_name: str | None = None
    lead_time_days: float = 7.0
    min_order_qty: float = 0.0
    explanation: str


class AffectedFinishedGood(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plant_code: str
    fg_code: str
    fg_description: str
    forecast_demand: float
    feasible_production: float
    unmet_demand: float
    bottleneck_component_code: str | None = None
    risk_status: str
    explanation: str


class FGPlanningResult(BaseModel):
    summary: dict[str, Any]
    component_requirements: list[ComponentRequirement] = []
    procurement_recommendations: list[ProcurementRecommendation] = []
    affected_finished_goods: list[AffectedFinishedGood] = []


class ShortageSummary(BaseModel):
    total_shortages_count: int
    critical_shortages_count: int
    shortages: list[ComponentRequirement] = []


class RecommendationSummary(BaseModel):
    total_recommendations_count: int
    recommendations: list[ProcurementRecommendation] = []
