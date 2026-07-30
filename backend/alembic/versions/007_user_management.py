"""Add username and must_change_password to users table

Revision ID: 007_user_management
Revises: 006_bom_schema
Create Date: 2026-07-30 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "007_user_management"
down_revision = "006_bom_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "username")
