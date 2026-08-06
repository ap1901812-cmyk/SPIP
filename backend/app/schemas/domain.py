from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PlantBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    location: str | None = None
    is_active: bool = True


class PlantCreate(PlantBase):
    pass


class PlantResponse(PlantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MaterialBase(BaseModel):
    code: str = Field(..., max_length=50)
    description: str = Field(..., max_length=255)
    material_type: str = Field(default="RAW_MATERIAL", max_length=50)
    base_uom: str = Field(default="KG", max_length=20)


class MaterialCreate(MaterialBase):
    pass


class MaterialResponse(MaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PlantMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plant_id: int
    material_id: int
    abc_class: str
    service_level_z: float
    review_period_days: int
    min_safety_stock: float | None = None
    max_safety_stock: float | None = None
    lead_time_days: float | None = 0.0
    safety_stock_override: float | None = None
    lead_time_1: float | None = None
    lead_time_2: float | None = None
    safety_stock_1: float | None = None
    safety_stock_2: float | None = None
    trigger_1: float | None = None
    trigger_2: float | None = None


class VendorBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    contact_email: str | None = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VendorMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    material_id: int
    is_primary: bool
    vendor_lead_time_days: float | None = None
    min_order_qty: float | None = None


class ConsumptionBase(BaseModel):
    plant_code: str
    material_code: str
    consumption_date: date
    quantity: float = Field(..., ge=0.0)
    uom: str = Field(default="KG", max_length=20)
    source: str = Field(default="SAP_MB51")


class ConsumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plant_id: int
    material_id: int
    consumption_date: date
    quantity: float
    uom: str
    source: str
    created_at: datetime


class InventorySnapshotBase(BaseModel):
    plant_code: str
    material_code: str
    snapshot_date: date
    usable_physical_stock: float = Field(..., ge=0.0)
    reserved_stock: float = Field(default=0.0, ge=0.0)
    blocked_stock: float = Field(default=0.0, ge=0.0)
    uom: str = Field(default="KG", max_length=20)
    source: str = Field(default="SAP_MB5B")


class InventorySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plant_id: int
    material_id: int
    snapshot_date: date
    usable_physical_stock: float
    reserved_stock: float
    blocked_stock: float
    uom: str
    source: str
    created_at: datetime


class PurchaseOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_id: int
    plant_id: int | None = None
    line_number: int
    material_id: int
    order_quantity: float
    open_quantity: float
    uom: str
    expected_delivery_date: date
    status: str


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    vendor_id: int
    plant_id: int | None = None
    status: str
    po_date: date
    lines: list[PurchaseOrderLineResponse] = []
