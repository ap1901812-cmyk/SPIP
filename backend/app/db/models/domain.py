from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.user import User


from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AllocationStatusEnum(enum.StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MaterialTypeEnum(enum.StrEnum):
    FG = "FG"
    RM = "RM"
    PM = "PM"

    @classmethod
    def normalize(cls, val: str | None) -> str:
        if not val:
            return cls.RM.value
        val_upper = val.strip().upper()
        if val_upper in ("FG", "FINISHED_GOOD", "FINISHED_GOODS"):
            return cls.FG.value
        if val_upper in ("PM", "PACKAGING", "PACKAGING_MATERIAL"):
            return cls.PM.value
        if val_upper in ("RM", "RAW_MATERIAL", "RAW_MATERIALS", "CHEMICAL"):
            return cls.RM.value
        return val_upper

    @classmethod
    def is_pm(cls, val: str | None) -> bool:
        return cls.normalize(val) == cls.PM.value

    @classmethod
    def is_rm(cls, val: str | None) -> bool:
        return cls.normalize(val) == cls.RM.value

    @classmethod
    def is_fg(cls, val: str | None) -> bool:
        return cls.normalize(val) == cls.FG.value


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant_materials: Mapped[list[PlantMaterial]] = relationship(
        "PlantMaterial", back_populates="plant"
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    material_type: Mapped[str] = mapped_column(String(50), nullable=False, default=MaterialTypeEnum.RM.value)
    material_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_capacity_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_uom: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant_materials: Mapped[list[PlantMaterial]] = relationship(
        "PlantMaterial", back_populates="material"
    )
    boms_as_fg: Mapped[list[BOM]] = relationship(
        "BOM", foreign_keys="[BOM.fg_material_id]", back_populates="fg_material", cascade="all, delete-orphan"
    )
    boms_as_component: Mapped[list[BOM]] = relationship(
        "BOM", foreign_keys="[BOM.component_material_id]", back_populates="component_material", cascade="all, delete-orphan"
    )


class BOM(Base):
    __tablename__ = "boms"
    __table_args__ = (
        UniqueConstraint("fg_material_id", "component_material_id", name="uq_bom_fg_component"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fg_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    fg_material: Mapped[Material] = relationship(
        "Material", foreign_keys=[fg_material_id], back_populates="boms_as_fg", lazy="joined"
    )
    component_material: Mapped[Material] = relationship(
        "Material", foreign_keys=[component_material_id], back_populates="boms_as_component", lazy="joined"
    )


class PlantMaterial(Base):
    __tablename__ = "plant_materials"
    __table_args__ = (UniqueConstraint("plant_id", "material_id", name="uq_plant_material"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    abc_class: Mapped[str] = mapped_column(String(5), nullable=False, default="B")
    service_level_z: Mapped[float] = mapped_column(Float, nullable=False, default=1.65)
    review_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    min_safety_stock: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    max_safety_stock: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_days: Mapped[float] = mapped_column(Float, nullable=False, default=7.0)
    safety_stock_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_stock_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_stock_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    trigger_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    trigger_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship(
        "Plant", back_populates="plant_materials", lazy="joined"
    )
    material: Mapped[Material] = relationship(
        "Material", back_populates="plant_materials", lazy="joined"
    )


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capacity_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_1_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_2_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VendorMaterial(Base):
    __tablename__ = "vendor_materials"
    __table_args__ = (
        UniqueConstraint("vendor_id", "material_id", "plant_id", name="uq_vendor_material_plant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vendor_lead_time_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_order_qty: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="joined")
    material: Mapped[Material] = relationship("Material", lazy="joined")
    plant: Mapped[Plant] = relationship("Plant", lazy="joined")


class ConsumptionHistory(Base):
    __tablename__ = "consumption_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumption_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="SAP_MB51")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    material: Mapped[Material] = relationship("Material", lazy="joined")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    usable_physical_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reserved_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blocked_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="SAP_MB5B")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    material: Mapped[Material] = relationship("Material", lazy="joined")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    po_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="joined")
    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        "PurchaseOrderLine", back_populates="po", cascade="all, delete-orphan", lazy="joined"
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    po_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    open_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONFIRMED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    po: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")
    material: Mapped[Material] = relationship("Material", lazy="joined")


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    allocation_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    allocated_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False, default="KG")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AllocationStatusEnum.DRAFT.value, index=True
    )

    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sap_reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    vehicle_capacity_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    proactive_flag: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recommendation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dispatch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    material: Mapped[Material] = relationship("Material", lazy="joined")
    vendor: Mapped[Vendor | None] = relationship("Vendor", lazy="joined")
    created_by_user: Mapped[User] = relationship(
        "User", foreign_keys=[created_by_user_id], lazy="joined"
    )
    approved_by_user: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_user_id], lazy="joined"
    )


class RMTotalityMapping(Base):
    __tablename__ = "rm_totality_mappings"
    __table_args__ = (
        UniqueConstraint("plant_id", "rm_material_id", "fg_group_name", name="uq_rm_totality_plant_rm_fg_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rm_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fg_group_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    consumption_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    rm_material: Mapped[Material] = relationship("Material", lazy="joined")


class PMOverride(Base):
    __tablename__ = "pm_overrides"
    __table_args__ = (
        UniqueConstraint("plant_id", "fg_material_id", "pm_material_id", name="uq_pm_override_plant_fg_pm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fg_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pm_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    override_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    fg_material: Mapped[Material] = relationship(
        "Material", foreign_keys=[fg_material_id], lazy="joined"
    )
    pm_material: Mapped[Material] = relationship(
        "Material", foreign_keys=[pm_material_id], lazy="joined"
    )
    updated_by_user: Mapped[User | None] = relationship(
        "User", foreign_keys=[updated_by_user_id], lazy="joined"
    )


class PlanningReadinessScore(Base):
    __tablename__ = "planning_readiness_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    missing_masters_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_parameters_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")


class ProcurementRecommendation(Base):
    __tablename__ = "procurement_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommended_qty: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_vendor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dispatch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    planning_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="PROACTIVE")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECOMMENDED", index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    material: Mapped[Material] = relationship("Material", lazy="joined")
    recommended_vendor: Mapped[Vendor | None] = relationship("Vendor", lazy="joined")


class ProductionReadinessRecord(Base):
    __tablename__ = "production_readiness_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fg_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="READY_TO_PRODUCE", index=True
    )
    blocking_rm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocking_pm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plant: Mapped[Plant] = relationship("Plant", lazy="joined")
    fg_material: Mapped[Material] = relationship("Material", lazy="joined")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_params_json: Mapped[str] = mapped_column(String(4000), nullable=False)
    results_json: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", lazy="joined")

