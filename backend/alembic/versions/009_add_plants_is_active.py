"""Add missing is_active column to plants table

Revision ID: 009_add_plants_is_active
Revises: 008_spip_v2_schema
Create Date: 2026-08-04 17:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "009_add_plants_is_active"
down_revision = "008_spip_v2_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plants",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("plants", "is_active")
