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

    # Statistical inputs
    average_daily_demand: float = Field(..., description="Average daily demand D")
    demand_std_dev: float = Field(..., description="Demand standard deviation sigma_d")
    observation_days_count: int = Field(
        ..., description="Number of valid historical consumption days"
    )

    # Lead time inputs
    lead_time_days: float = Field(..., description="Lead time in days LT")
    lead_time_source: str = Field(..., description="Source of lead time value")

    # Safety stock inputs
    service_level_z: float = Field(..., description="Cycle service level Z factor")
    abc_class: str = Field(..., description="ABC classification (A, B, C)")
    safety_stock: float = Field(..., description="Calculated safety stock SS")
    is_safety_stock_overridden: bool = False

    # Availability inputs & components
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
    planning_availability: float = Field(..., description="Effective Planning Availability AI")

    # Decision thresholds
    demand_during_lead_time: float = Field(..., description="Demand during lead time D x LT")
    reorder_point: float = Field(..., description="Reorder point ROP = (D x LT) + SS")

    # Deterministic status & explainability
    criticality_status: Literal["CRITICAL", "WARNING", "HEALTHY"]
    explanation: str = Field(..., description="Explainable audit reasoning for status decision")
