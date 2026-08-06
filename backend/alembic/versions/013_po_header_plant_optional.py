"""make po header plant optional and add plant_id to purchase_order_lines

Revision ID: 013_po_header_plant_optional
Revises: 012_make_vendor_material_global
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '013_po_header_plant_optional'
down_revision: Union[str, None] = '012_make_vendor_material_global'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make plant_id optional on purchase_orders
    op.alter_column('purchase_orders', 'plant_id', existing_type=sa.Integer(), nullable=True)

    # 2. Add plant_id to purchase_order_lines if not exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('purchase_order_lines')]
    if 'plant_id' not in cols:
        op.add_column('purchase_order_lines', sa.Column('plant_id', sa.Integer(), sa.ForeignKey('plants.id', ondelete='CASCADE'), nullable=True))
        op.create_index('ix_purchase_order_lines_plant_id', 'purchase_order_lines', ['plant_id'])


def downgrade() -> None:
    pass
