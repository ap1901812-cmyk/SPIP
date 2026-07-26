from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AllocationCreateSchema(BaseModel):
    plant_code: str
    material_code: str
    vendor_code: str | None = None
    allocated_quantity: float = Field(..., gt=0.0, description="Allocated quantity must be > 0")
    uom: str = Field(default="KG", description="Unit of measure")


class AllocationUpdateSchema(BaseModel):
    allocated_quantity: float | None = Field(default=None, gt=0.0)
    vendor_code: str | None = None
    version: int = Field(
        ..., description="Expected current version for optimistic concurrency check"
    )


class AllocationRejectSchema(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=500)


class AllocationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    allocation_number: str
    plant_code: str
    plant_name: str
    material_code: str
    material_description: str
    vendor_code: str | None = None
    vendor_name: str | None = None
    allocated_quantity: float
    uom: str
    status: str
    created_by_email: str
    approved_by_email: str | None = None
    rejection_reason: str | None = None
    sap_reference_id: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
