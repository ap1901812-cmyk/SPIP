"""Create allocations table for Phase 6 workflow

Revision ID: 003_allocations_schema
Revises: 002_domain_schema
Create Date: 2026-07-26 18:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "003_allocations_schema"
down_revision = "002_domain_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allocation_number", sa.String(length=50), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("allocated_quantity", sa.Float(), nullable=False),
        sa.Column("uom", sa.String(length=20), server_default="KG", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="DRAFT", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("sap_reference_id", sa.String(length=50), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
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
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_allocations_allocation_number"),
        "allocations",
        ["allocation_number"],
        unique=True,
    )

    op.create_index(op.f("ix_allocations_id"), "allocations", ["id"], unique=False)
    op.create_index(
        op.f("ix_allocations_material_id"), "allocations", ["material_id"], unique=False
    )
    op.create_index(op.f("ix_allocations_plant_id"), "allocations", ["plant_id"], unique=False)
    op.create_index(op.f("ix_allocations_status"), "allocations", ["status"], unique=False)
    op.create_index(op.f("ix_allocations_vendor_id"), "allocations", ["vendor_id"], unique=False)
    op.create_index(
        op.f("ix_allocations_created_by_user_id"),
        "allocations",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_allocations_created_by_user_id"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_vendor_id"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_status"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_plant_id"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_material_id"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_id"), table_name="allocations")
    op.drop_index(op.f("ix_allocations_allocation_number"), table_name="allocations")
    op.drop_table("allocations")
