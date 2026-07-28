from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bom import BOMDetailResponse
from app.schemas.domain import InventorySnapshotResponse, PlantMaterialResponse


class FinishedGoodSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: str
    base_uom: str
    material_type: str = "FG"
    plant_count: int = 0
    component_count: int = 0
    created_at: datetime
    updated_at: datetime


class FinishedGoodDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: str
    base_uom: str
    material_type: str = "FG"
    created_at: datetime
    updated_at: datetime
    plant_materials: list[PlantMaterialResponse] = []
    inventory_snapshots: list[InventorySnapshotResponse] = []
    rm_components_count: int = 0
    pm_components_count: int = 0


class FGBOMExpansionResponse(BaseModel):
    fg_material_id: int
    fg_code: str
    fg_description: str
    rm_components: list[BOMDetailResponse] = []
    pm_components: list[BOMDetailResponse] = []
