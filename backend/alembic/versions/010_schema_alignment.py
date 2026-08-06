"""Align database schema for inventory_snapshots, vendors, and purchase_orders

Revision ID: 010_schema_alignment
Revises: 009_add_plants_is_active
Create Date: 2026-08-04 18:00:00.000000

AUDIT OF OPERATIONS vs HISTORICAL MIGRATIONS:
1. vendors.contact_email: Created in 002_domain_schema.py (Line 108). Unconditional add_column causes DuplicateColumn error.
2. vendors.is_active: Created in 002_domain_schema.py (Line 109). Unconditional add_column causes DuplicateColumn error.
3. inventory_snapshots (unrestricted_stock, quality_inspection_stock, in_transit_stock): Present in domain models, missing in migrations 001-009.
4. purchase_orders (material_id, ordered_quantity, delivered_quantity, order_date, expected_delivery_date, actual_delivery_date): Present in domain models, missing in migrations 001-009.
5. purchase_order_lines (line_item_number, quantity): Present in domain models, missing in migrations 001-009.
"""

import logging
from typing import Any
import sqlalchemy as sa
from alembic import op

revision = "010_schema_alignment"
down_revision = "009_add_plants_is_active"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def get_inspector() -> sa.Inspector:
    bind = op.get_bind()
    return sa.inspect(bind)


def safe_add_column(
    table_name: str,
    column: sa.Column,
    report: dict[str, list[str]],
    origin_note: str = "",
) -> None:
    inspector = get_inspector()
    if not inspector.has_table(table_name):
        msg = f"Table '{table_name}' is missing when attempting to add column '{column.name}'"
        logger.warning(f"SCHEMA ALIGNMENT: [Missing] {msg}")
        report["inconsistencies"].append(msg)
        return

    existing_cols = [c["name"] for c in inspector.get_columns(table_name)]
    if column.name in existing_cols:
        reason = f"Column '{column.name}' on table '{table_name}' already exists" + (
            f" (origin: {origin_note})" if origin_note else ""
        )
        logger.info(f"SCHEMA ALIGNMENT: [Already exists] {reason}")
        report["already_present"].append(f"{table_name}.{column.name} ({origin_note or 'existing'})")
        report["skipped"].append(f"add_column({table_name}.{column.name}) - Reason: Already exists")
    else:
        op.add_column(table_name, column)
        msg = f"Added column '{column.name}' to table '{table_name}'"
        logger.info(f"SCHEMA ALIGNMENT: [Created] {msg}")
        report["created"].append(f"{table_name}.{column.name}")


def safe_create_index(
    index_name: str,
    table_name: str,
    columns: list[str],
    report: dict[str, list[str]],
    **kwargs: Any,
) -> None:
    inspector = get_inspector()
    if not inspector.has_table(table_name):
        msg = f"Table '{table_name}' is missing when attempting to create index '{index_name}'"
        logger.warning(f"SCHEMA ALIGNMENT: [Missing] {msg}")
        report["inconsistencies"].append(msg)
        return

    existing_indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    if index_name in existing_indexes:
        logger.info(f"SCHEMA ALIGNMENT: [Already exists] Index '{index_name}' on table '{table_name}'")
        report["already_present"].append(f"index {index_name} on {table_name}")
        report["skipped"].append(f"create_index({index_name}) - Reason: Already exists")
    else:
        op.create_index(index_name, table_name, columns, **kwargs)
        logger.info(f"SCHEMA ALIGNMENT: [Created] Index '{index_name}' on table '{table_name}'")
        report["created"].append(f"index {index_name} on {table_name}")


def safe_create_unique_constraint(
    constraint_name: str,
    table_name: str,
    columns: list[str],
    report: dict[str, list[str]],
) -> None:
    inspector = get_inspector()
    if not inspector.has_table(table_name):
        msg = f"Table '{table_name}' is missing when attempting to create unique constraint '{constraint_name}'"
        logger.warning(f"SCHEMA ALIGNMENT: [Missing] {msg}")
        report["inconsistencies"].append(msg)
        return

    existing_ucs = [uc["name"] for uc in inspector.get_unique_constraints(table_name)]
    if constraint_name in existing_ucs:
        logger.info(f"SCHEMA ALIGNMENT: [Already exists] Unique constraint '{constraint_name}' on table '{table_name}'")
        report["already_present"].append(f"unique_constraint {constraint_name} on {table_name}")
        report["skipped"].append(f"create_unique_constraint({constraint_name}) - Reason: Already exists")
    else:
        op.create_unique_constraint(constraint_name, table_name, columns)
        logger.info(f"SCHEMA ALIGNMENT: [Created] Unique constraint '{constraint_name}' on table '{table_name}'")
        report["created"].append(f"unique_constraint {constraint_name} on {table_name}")


def safe_create_table(
    table_name: str,
    *columns: Any,
    report: dict[str, list[str]],
    **kwargs: Any,
) -> None:
    inspector = get_inspector()
    if inspector.has_table(table_name):
        logger.info(f"SCHEMA ALIGNMENT: [Already exists] Table '{table_name}' already exists")
        report["already_present"].append(f"table {table_name}")
        report["skipped"].append(f"create_table({table_name}) - Reason: Already exists")
    else:
        op.create_table(table_name, *columns, **kwargs)
        logger.info(f"SCHEMA ALIGNMENT: [Created] Table '{table_name}'")
        report["created"].append(f"table {table_name}")


def safe_create_foreign_key(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    report: dict[str, list[str]],
    **kwargs: Any,
) -> None:
    inspector = get_inspector()
    if not inspector.has_table(source_table):
        msg = f"Table '{source_table}' is missing when attempting to create foreign key '{constraint_name}'"
        logger.warning(f"SCHEMA ALIGNMENT: [Missing] {msg}")
        report["inconsistencies"].append(msg)
        return

    existing_fks = [fk["name"] for fk in inspector.get_foreign_keys(source_table)]
    if constraint_name in existing_fks:
        logger.info(f"SCHEMA ALIGNMENT: [Already exists] Foreign key '{constraint_name}' on table '{source_table}'")
        report["already_present"].append(f"foreign_key {constraint_name} on {source_table}")
        report["skipped"].append(f"create_foreign_key({constraint_name}) - Reason: Already exists")
    else:
        op.create_foreign_key(
            constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs
        )
        logger.info(f"SCHEMA ALIGNMENT: [Created] Foreign key '{constraint_name}' on table '{source_table}'")
        report["created"].append(f"foreign_key {constraint_name} on {source_table}")


def safe_drop_column(table_name: str, column_name: str) -> None:
    inspector = get_inspector()
    if not inspector.has_table(table_name):
        logger.warning(f"SCHEMA ALIGNMENT: [Missing] Table '{table_name}' does not exist for dropping column '{column_name}'")
        return

    existing_cols = [c["name"] for c in inspector.get_columns(table_name)]
    if column_name in existing_cols:
        op.drop_column(table_name, column_name)
        logger.info(f"SCHEMA ALIGNMENT: [Dropped] Column '{column_name}' from table '{table_name}'")
    else:
        logger.info(f"SCHEMA ALIGNMENT: [Skipped] Column '{column_name}' on table '{table_name}' was not present to drop")


def upgrade() -> None:
    report: dict[str, list[str]] = {
        "created": [],
        "skipped": [],
        "already_present": [],
        "inconsistencies": [],
    }

    logger.info("=== STARTING MIGRATION 010 SCHEMA ALIGNMENT ===")

    # 1. Add missing columns to inventory_snapshots
    safe_add_column(
        "inventory_snapshots",
        sa.Column("unrestricted_stock", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "inventory_snapshots",
        sa.Column("quality_inspection_stock", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "inventory_snapshots",
        sa.Column("in_transit_stock", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        report=report,
        origin_note="SQLAlchemy domain model",
    )

    # 2. Add missing columns to vendors
    safe_add_column(
        "vendors",
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        report=report,
        origin_note="002_domain_schema.py Line 108",
    )
    safe_add_column(
        "vendors",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        report=report,
        origin_note="002_domain_schema.py Line 109",
    )

    # 3. Add missing columns to purchase_orders
    safe_add_column(
        "purchase_orders",
        sa.Column("material_id", sa.Integer(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_orders",
        sa.Column("ordered_quantity", sa.Float(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_orders",
        sa.Column("delivered_quantity", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_orders",
        sa.Column("order_date", sa.Date(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_orders",
        sa.Column("actual_delivery_date", sa.Date(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )

    # 4. Add missing columns to purchase_order_lines
    safe_add_column(
        "purchase_order_lines",
        sa.Column("line_item_number", sa.Integer(), nullable=True),
        report=report,
        origin_note="SQLAlchemy domain model",
    )
    safe_add_column(
        "purchase_order_lines",
        sa.Column("quantity", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        report=report,
        origin_note="SQLAlchemy domain model",
    )

    # 5. Create missing planning_execution_records table
    safe_create_table(
        "planning_execution_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=True),
        sa.Column("execution_status", sa.String(length=30), server_default="SUCCESS", nullable=False),
        sa.Column("duration_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("modules_executed_json", sa.String(length=1000), nullable=False),
        sa.Column("modules_skipped_json", sa.String(length=1000), nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("details_json", sa.String(length=4000), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        report=report,
    )
    safe_create_index("ix_planning_execution_records_id", "planning_execution_records", ["id"], report=report)
    safe_create_index("ix_planning_execution_records_plant_id", "planning_execution_records", ["plant_id"], report=report)
    safe_create_index("ix_planning_execution_records_material_id", "planning_execution_records", ["material_id"], report=report)
    safe_create_index("ix_planning_execution_records_execution_status", "planning_execution_records", ["execution_status"], report=report)

    # 6. Add missing columns to allocations table
    safe_add_column("allocations", sa.Column("recommendation_id", sa.Integer(), nullable=True), report=report, origin_note="SQLAlchemy domain model")
    safe_add_column("allocations", sa.Column("dispatch_date", sa.Date(), nullable=True), report=report, origin_note="SQLAlchemy domain model")
    safe_add_column("allocations", sa.Column("expected_arrival_date", sa.Date(), nullable=True), report=report, origin_note="SQLAlchemy domain model")
    safe_add_column("allocations", sa.Column("allocation_notes", sa.String(length=500), nullable=True), report=report, origin_note="SQLAlchemy domain model")
    safe_add_column("allocations", sa.Column("notification_payload_json", sa.String(length=4000), nullable=True), report=report, origin_note="SQLAlchemy domain model")

    # 7. Add missing columns to procurement_recommendations table
    safe_add_column("procurement_recommendations", sa.Column("recommended_procurement_date", sa.Date(), nullable=True), report=report, origin_note="SQLAlchemy domain model")
    safe_add_column("procurement_recommendations", sa.Column("explanation_json", sa.String(length=4000), nullable=True), report=report, origin_note="SQLAlchemy domain model")

    # 8. Create missing forecast_records table
    safe_create_table(
        "forecast_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=50), server_default="MOVING_AVERAGE", nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("forecast_horizon_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("forecast_quantity", sa.Float(), nullable=False),
        sa.Column("actual_consumption", sa.Float(), nullable=True),
        sa.Column("wmape_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("details_json", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        report=report,
    )
    safe_create_index("ix_forecast_records_id", "forecast_records", ["id"], report=report)
    safe_create_index("ix_forecast_records_plant_id", "forecast_records", ["plant_id"], report=report)
    safe_create_index("ix_forecast_records_material_id", "forecast_records", ["material_id"], report=report)
    safe_create_index("ix_forecast_records_forecast_date", "forecast_records", ["forecast_date"], report=report)

    # 9. Alter simulation_runs columns to Text type
    try:
        op.alter_column("simulation_runs", "input_params_json", type_=sa.Text(), existing_type=sa.String(length=4000))
        op.alter_column("simulation_runs", "results_json", type_=sa.Text(), existing_type=sa.String(length=4000))
    except Exception as e:
        logger.warning(f"SCHEMA ALIGNMENT: Could not alter simulation_runs text columns: {e}")

    logger.info("=== SCHEMA ALIGNMENT REPORT (010_schema_alignment) ===")
    logger.info("Objects Created: %s", report["created"])
    logger.info("Objects Already Present: %s", report["already_present"])
    logger.info("Objects Skipped: %s", report["skipped"])
    logger.info("Remaining Inconsistencies: %s", report["inconsistencies"])
    logger.info("=====================================================")


def downgrade() -> None:
    safe_drop_column("purchase_order_lines", "quantity")
    safe_drop_column("purchase_order_lines", "line_item_number")

    safe_drop_column("purchase_orders", "actual_delivery_date")
    safe_drop_column("purchase_orders", "expected_delivery_date")
    safe_drop_column("purchase_orders", "order_date")
    safe_drop_column("purchase_orders", "delivered_quantity")
    safe_drop_column("purchase_orders", "ordered_quantity")
    safe_drop_column("purchase_orders", "material_id")

    safe_drop_column("vendors", "is_active")
    safe_drop_column("vendors", "contact_email")

    safe_drop_column("inventory_snapshots", "in_transit_stock")
    safe_drop_column("inventory_snapshots", "quality_inspection_stock")
    safe_drop_column("inventory_snapshots", "unrestricted_stock")
