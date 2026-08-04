from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlanningCalculationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plant_code: str
    plant_name: str
    material_code: str
    material_description: str
    base_uom: str
    as_of_timestamp: datetime

    # Statistical inputs & Consumption Intelligence
    average_daily_demand: float = Field(..., description="Average daily demand D")
    demand_std_dev: float = Field(..., description="Demand standard deviation sigma_d")
    observation_days_count: int = Field(
        ..., description="Number of valid historical consumption days"
    )
    consumption_trend: str = Field("STABLE", description="Consumption trend (INCREASING, DECREASING, STABLE)")
    consumption_variability: float = Field(0.0, description="Coefficient of variation CV = sigma_d / D_avg")

    # Lead time inputs (RMPM Dual Lead Times)
    lead_time_1: float = Field(7.0, description="RMPM Lead Time 1 (Initial Procurement LT)")
    lead_time_2: float = Field(3.0, description="RMPM Lead Time 2 (Regular Replenishment LT)")
    lead_time_days: float = Field(..., description="Legacy Lead time in days LT")
    lead_time_source: str = Field(..., description="Source of lead time value")

    # Safety stock inputs (RMPM Dual Safety Stocks)
    service_level_z: float = Field(..., description="Cycle service level Z factor")
    abc_class: str = Field(..., description="ABC classification (A, B, C)")
    safety_stock_1: float = Field(0.0, description="RMPM Safety Stock 1 (Initial Cycle SS)")
    safety_stock_2: float = Field(0.0, description="RMPM Safety Stock 2 (Regular Replenishment SS)")
    safety_stock: float = Field(..., description="Legacy calculated safety stock SS")
    is_safety_stock_overridden: bool = False

    # Availability inputs & Inventory Intelligence
    usable_physical_stock: float = Field(
        ..., description="Usable physical stock (net of reserved/blocked)"
    )
    reserved_stock_info: float = Field(
        ..., description="Reserved stock already excluded from usable stock"
    )
    blocked_stock_info: float = Field(
        ..., description="Blocked stock already excluded from usable stock"
    )
    eligible_incoming_po_qty: float = Field(
        ..., description="Eligible confirmed incoming supply within horizon"
    )
    committed_allocations: float = Field(..., description="Already committed allocations")
    planning_availability: float = Field(..., description="Effective Planning Available Inventory AI")
    days_of_inventory: float = Field(999.0, description="Days of Inventory DOI = AI / D_avg")

    # Decision thresholds (RMPM Triggers)
    trigger_1: float = Field(0.0, description="RMPM Trigger 1 = (D_avg * LT-1) + SS-1")
    trigger_2: float = Field(0.0, description="RMPM Trigger 2 = (D_avg * LT-2) + SS-2")
    demand_during_lead_time: float = Field(..., description="Demand during lead time D x LT")
    reorder_point: float = Field(..., description="Legacy Reorder point ROP = (D x LT) + SS")

    # Deterministic status & explainability
    rmpm_material_status: str = Field("HEALTHY", description="RMPM 4-tier status (CRITICAL, REORDER_REQUIRED, LOW_STOCK, HEALTHY)")
    criticality_status: Literal["CRITICAL", "WARNING", "HEALTHY"]
    explanation: str = Field(..., description="Explainable audit reasoning for status decision")
