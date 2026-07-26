"""Create domain tables for multi-plant schema

Revision ID: 002_domain_schema
Revises: 001_security_schema
Create Date: 2026-07-26 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "002_domain_schema"
down_revision = "001_security_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plants_code"), "plants", ["code"], unique=True)
    op.create_index(op.f("ix_plants_id"), "plants", ["id"], unique=False)

    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("material_type", sa.String(length=50), nullable=False),
        sa.Column("base_uom", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_code"), "materials", ["code"], unique=True)
    op.create_index(op.f("ix_materials_id"), "materials", ["id"], unique=False)

    op.create_table(
        "plant_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("abc_class", sa.String(length=5), nullable=False),
        sa.Column("service_level_z", sa.Float(), nullable=False),
        sa.Column("review_period_days", sa.Integer(), nullable=False),
        sa.Column("min_safety_stock", sa.Float(), nullable=True),
        sa.Column("max_safety_stock", sa.Float(), nullable=True),
        sa.Column("lead_time_days", sa.Float(), nullable=False),
        sa.Column("safety_stock_override", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "material_id", name="uq_plant_material"),
    )
    op.create_index(
        op.f("ix_plant_materials_material_id"), "plant_materials", ["material_id"], unique=False
    )
    op.create_index(
        op.f("ix_plant_materials_plant_id"), "plant_materials", ["plant_id"], unique=False
    )

    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendors_code"), "vendors", ["code"], unique=True)
    op.create_index(op.f("ix_vendors_id"), "vendors", ["id"], unique=False)

    op.create_table(
        "vendor_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("vendor_lead_time_days", sa.Float(), nullable=True),
        sa.Column("min_order_qty", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vendor_id", "material_id", "plant_id", name="uq_vendor_material_plant"
        ),
    )
    op.create_index(
        op.f("ix_vendor_materials_material_id"), "vendor_materials", ["material_id"], unique=False
    )
    op.create_index(
        op.f("ix_vendor_materials_plant_id"), "vendor_materials", ["plant_id"], unique=False
    )
    op.create_index(
        op.f("ix_vendor_materials_vendor_id"), "vendor_materials", ["vendor_id"], unique=False
    )

    op.create_table(
        "consumption_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("consumption_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("uom", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_consumption_history_consumption_date"),
        "consumption_history",
        ["consumption_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_consumption_history_id"), "consumption_history", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_consumption_history_material_id"),
        "consumption_history",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_consumption_history_plant_id"),
        "consumption_history",
        ["plant_id"],
        unique=False,
    )

    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("usable_physical_stock", sa.Float(), nullable=False),
        sa.Column("reserved_stock", sa.Float(), nullable=False),
        sa.Column("blocked_stock", sa.Float(), nullable=False),
        sa.Column("uom", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_snapshots_id"), "inventory_snapshots", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_inventory_snapshots_material_id"),
        "inventory_snapshots",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_snapshots_plant_id"),
        "inventory_snapshots",
        ["plant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_snapshots_snapshot_date"),
        "inventory_snapshots",
        ["snapshot_date"],
        unique=False,
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("po_number", sa.String(length=50), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("po_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_orders_id"), "purchase_orders", ["id"], unique=False)
    op.create_index(
        op.f("ix_purchase_orders_plant_id"), "purchase_orders", ["plant_id"], unique=False
    )
    op.create_index(
        op.f("ix_purchase_orders_po_number"), "purchase_orders", ["po_number"], unique=True
    )
    op.create_index(
        op.f("ix_purchase_orders_vendor_id"), "purchase_orders", ["vendor_id"], unique=False
    )

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("po_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("order_quantity", sa.Float(), nullable=False),
        sa.Column("open_quantity", sa.Float(), nullable=False),
        sa.Column("uom", sa.String(length=20), nullable=False),
        sa.Column("expected_delivery_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_purchase_order_lines_id"), "purchase_order_lines", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_purchase_order_lines_material_id"),
        "purchase_order_lines",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_order_lines_po_id"), "purchase_order_lines", ["po_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_order_lines_po_id"), table_name="purchase_order_lines")
    op.drop_index(
        op.f("ix_purchase_order_lines_material_id"), table_name="purchase_order_lines"
    )
    op.drop_index(op.f("ix_purchase_order_lines_id"), table_name="purchase_order_lines")
    op.drop_table("purchase_order_lines")

    op.drop_index(op.f("ix_purchase_orders_vendor_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_po_number"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_plant_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_id"), table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index(
        op.f("ix_inventory_snapshots_snapshot_date"), table_name="inventory_snapshots"
    )
    op.drop_index(op.f("ix_inventory_snapshots_plant_id"), table_name="inventory_snapshots")
    op.drop_index(
        op.f("ix_inventory_snapshots_material_id"), table_name="inventory_snapshots"
    )
    op.drop_index(op.f("ix_inventory_snapshots_id"), table_name="inventory_snapshots")
    op.drop_table("inventory_snapshots")

    op.drop_index(op.f("ix_consumption_history_plant_id"), table_name="consumption_history")
    op.drop_index(
        op.f("ix_consumption_history_material_id"), table_name="consumption_history"
    )
    op.drop_index(op.f("ix_consumption_history_id"), table_name="consumption_history")
    op.drop_index(
        op.f("ix_consumption_history_consumption_date"), table_name="consumption_history"
    )
    op.drop_table("consumption_history")

    op.drop_index(op.f("ix_vendor_materials_vendor_id"), table_name="vendor_materials")
    op.drop_index(op.f("ix_vendor_materials_plant_id"), table_name="vendor_materials")
    op.drop_index(op.f("ix_vendor_materials_material_id"), table_name="vendor_materials")
    op.drop_table("vendor_materials")

    op.drop_index(op.f("ix_vendors_id"), table_name="vendors")
    op.drop_index(op.f("ix_vendors_code"), table_name="vendors")
    op.drop_table("vendors")

    op.drop_index(op.f("ix_plant_materials_plant_id"), table_name="plant_materials")
    op.drop_index(op.f("ix_plant_materials_material_id"), table_name="plant_materials")
    op.drop_table("plant_materials")

    op.drop_index(op.f("ix_materials_id"), table_name="materials")
    op.drop_index(op.f("ix_materials_code"), table_name="materials")
    op.drop_table("materials")

    op.drop_index(op.f("ix_plants_id"), table_name="plants")
    op.drop_index(op.f("ix_plants_code"), table_name="plants")
    op.drop_table("plants")
