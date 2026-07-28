"""Create boms table for SPIP v1.5 Sprint 1

Revision ID: 006_bom_schema
Revises: 005_jobs_schema
Create Date: 2026-07-28 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "006_bom_schema"
down_revision = "005_jobs_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fg_material_id", sa.Integer(), nullable=False),
        sa.Column("component_material_id", sa.Integer(), nullable=False),
        sa.Column("required_quantity", sa.Float(), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=20), server_default="KG", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(["fg_material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fg_material_id", "component_material_id", name="uq_bom_fg_component"),
    )
    op.create_index(op.f("ix_boms_id"), "boms", ["id"], unique=False)
    op.create_index(op.f("ix_boms_fg_material_id"), "boms", ["fg_material_id"], unique=False)
    op.create_index(
        op.f("ix_boms_component_material_id"), "boms", ["component_material_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_boms_component_material_id"), table_name="boms")
    op.drop_index(op.f("ix_boms_fg_material_id"), table_name="boms")
    op.drop_index(op.f("ix_boms_id"), table_name="boms")
    op.drop_table("boms")
