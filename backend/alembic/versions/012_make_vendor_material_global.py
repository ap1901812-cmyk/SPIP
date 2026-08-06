"""make vendor material global

Revision ID: 012_make_vendor_material_global
Revises: 011_workbook_import_tables
Create Date: 2026-08-05 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_make_vendor_material_global'
down_revision: Union[str, None] = '011_workbook_import_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing unique constraint
    op.drop_constraint('uq_vendor_material_plant', 'vendor_materials', type_='unique')
    
    # Drop plant_id foreign key constraint and index
    op.drop_constraint('vendor_materials_plant_id_fkey', 'vendor_materials', type_='foreignkey')
    op.drop_index('ix_vendor_materials_plant_id', table_name='vendor_materials')
    
    # Drop plant_id column
    op.drop_column('vendor_materials', 'plant_id')
    
    # Create new unique constraint
    op.create_unique_constraint('uq_vendor_material', 'vendor_materials', ['vendor_id', 'material_id'])


def downgrade() -> None:
    # Drop new constraint
    op.drop_constraint('uq_vendor_material', 'vendor_materials', type_='unique')
    
    # Add plant_id back
    op.add_column('vendor_materials', sa.Column('plant_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_index('ix_vendor_materials_plant_id', 'vendor_materials', ['plant_id'], unique=False)
    op.create_foreign_key('vendor_materials_plant_id_fkey', 'vendor_materials', 'plants', ['plant_id'], ['id'], ondelete='CASCADE')
    
    # Re-add old constraint
    op.create_unique_constraint('uq_vendor_material_plant', 'vendor_materials', ['vendor_id', 'material_id', 'plant_id'])
