from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.domain import MaterialResponse


class BOMBase(BaseModel):
    fg_material_id: int
    component_material_id: int
    required_quantity: float = Field(..., gt=0.0)
    unit_of_measure: str = Field(default="KG", max_length=20)
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True


class BOMCreate(BOMBase):
    pass


class BOMUpdate(BaseModel):
    required_quantity: float | None = Field(default=None, gt=0.0)
    unit_of_measure: str | None = Field(default=None, max_length=20)
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool | None = None


class BOMResponse(BOMBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class BOMDetailResponse(BOMResponse):
    fg_material: MaterialResponse | None = None
    component_material: MaterialResponse | None = None
