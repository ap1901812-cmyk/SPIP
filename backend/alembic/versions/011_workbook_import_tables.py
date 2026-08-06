"""Add tables and columns for Enterprise Workbook Import Framework

Revision ID: 011_workbook_import_tables
Revises: 010_schema_alignment
Create Date: 2026-08-05 14:00:00.000000
"""

import logging
import sqlalchemy as sa
from alembic import op

revision = "011_workbook_import_tables"
down_revision = "010_schema_alignment"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def get_inspector() -> sa.Inspector:
    bind = op.get_bind()
    return sa.inspect(bind)


def upgrade() -> None:
    inspector = get_inspector()

    # 1. Add storage_capacity_tons to plants if missing
    if inspector.has_table("plants"):
        cols = [c["name"] for c in inspector.get_columns("plants")]
        if "storage_capacity_tons" not in cols:
            op.add_column("plants", sa.Column("storage_capacity_tons", sa.Float(), nullable=True))

    # 2. vehicle_masters
    if not inspector.has_table("vehicle_masters"):
        op.create_table(
            "vehicle_masters",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("vehicle_type_code", sa.String(50), unique=True, index=True, nullable=False),
            sa.Column("vehicle_type_name", sa.String(255), nullable=False),
            sa.Column("capacity_tons", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("capacity_cbm", sa.Float(), nullable=True),
            sa.Column("cost_per_km", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 3. monthly_production_plans
    if not inspector.has_table("monthly_production_plans"):
        op.create_table(
            "monthly_production_plans",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("month", sa.Integer(), nullable=False),
            sa.Column("planned_production_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("plant_id", "material_id", "year", "month", name="uq_monthly_prod_plan"),
        )

    # 4. daily_ibp_plans
    if not inspector.has_table("daily_ibp_plans"):
        op.create_table(
            "daily_ibp_plans",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("plan_date", sa.Date(), nullable=False, index=True),
            sa.Column("required_daily_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("plant_id", "material_id", "plan_date", name="uq_daily_ibp_plan"),
        )


def downgrade() -> None:
    pass
