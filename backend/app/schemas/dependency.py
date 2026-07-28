from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WhereUsedEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bom_id: int
    fg_material_id: int
    fg_code: str
    fg_description: str
    fg_material_type: str = "FG"
    required_quantity: float
    unit_of_measure: str
    is_active: bool


class WhereUsedResponse(BaseModel):
    component_material_id: int
    component_code: str
    component_description: str
    component_type: str
    total_where_used: int
    where_used: list[WhereUsedEntry] = []


class MaterialDependencyResponse(BaseModel):
    material_id: int
    material_code: str
    material_description: str
    material_type: str
    upstream_finished_goods: list[WhereUsedEntry] = []
    downstream_components: list[WhereUsedEntry] = []
