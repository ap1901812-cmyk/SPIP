"""Expand schema for SPIP V2 enterprise tables and domain model extensions

Revision ID: 008_spip_v2_schema
Revises: 007_user_management
Create Date: 2026-08-04 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "008_spip_v2_schema"
down_revision = "007_user_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend materials table
    op.add_column("materials", sa.Column("material_group", sa.String(length=50), nullable=True))
    op.add_column("materials", sa.Column("storage_capacity_limit", sa.Float(), nullable=True))

    # 2. Extend vendors table
    op.add_column("vendors", sa.Column("capacity_per_day", sa.Float(), nullable=True))
    op.add_column("vendors", sa.Column("lead_time_1_days", sa.Float(), nullable=True))
    op.add_column("vendors", sa.Column("lead_time_2_days", sa.Float(), nullable=True))

    # 3. Extend plant_materials table (RMPM dual parameters per plant-material)
    op.add_column("plant_materials", sa.Column("lead_time_1", sa.Float(), nullable=True))
    op.add_column("plant_materials", sa.Column("lead_time_2", sa.Float(), nullable=True))
    op.add_column("plant_materials", sa.Column("safety_stock_1", sa.Float(), nullable=True))
    op.add_column("plant_materials", sa.Column("safety_stock_2", sa.Float(), nullable=True))
    op.add_column("plant_materials", sa.Column("trigger_1", sa.Float(), nullable=True))
    op.add_column("plant_materials", sa.Column("trigger_2", sa.Float(), nullable=True))

    # 4. Extend allocations table
    op.add_column("allocations", sa.Column("vehicle_capacity_used", sa.Float(), nullable=True))
    op.add_column(
        "allocations",
        sa.Column("proactive_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column("allocations", sa.Column("recommendation_reason", sa.String(length=500), nullable=True))
    op.add_column("allocations", sa.Column("dispatch_date", sa.Date(), nullable=True))
    op.add_column("allocations", sa.Column("expected_arrival_date", sa.Date(), nullable=True))

    # 5. Create rm_totality_mappings table
    op.create_table(
        "rm_totality_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("rm_material_id", sa.Integer(), nullable=False),
        sa.Column("fg_group_name", sa.String(length=100), nullable=False),
        sa.Column("consumption_ratio", sa.Float(), server_default=sa.text("1.0"), nullable=False),
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
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rm_material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "rm_material_id", "fg_group_name", name="uq_rm_totality_plant_rm_fg_group"),
    )
    op.create_index(op.f("ix_rm_totality_mappings_fg_group_name"), "rm_totality_mappings", ["fg_group_name"], unique=False)
    op.create_index(op.f("ix_rm_totality_mappings_id"), "rm_totality_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_rm_totality_mappings_plant_id"), "rm_totality_mappings", ["plant_id"], unique=False)
    op.create_index(op.f("ix_rm_totality_mappings_rm_material_id"), "rm_totality_mappings", ["rm_material_id"], unique=False)

    # 6. Create pm_overrides table
    op.create_table(
        "pm_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("fg_material_id", sa.Integer(), nullable=False),
        sa.Column("pm_material_id", sa.Integer(), nullable=False),
        sa.Column("override_ratio", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["pm_material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "fg_material_id", "pm_material_id", name="uq_pm_override_plant_fg_pm"),
    )
    op.create_index(op.f("ix_pm_overrides_fg_material_id"), "pm_overrides", ["fg_material_id"], unique=False)
    op.create_index(op.f("ix_pm_overrides_id"), "pm_overrides", ["id"], unique=False)
    op.create_index(op.f("ix_pm_overrides_plant_id"), "pm_overrides", ["plant_id"], unique=False)
    op.create_index(op.f("ix_pm_overrides_pm_material_id"), "pm_overrides", ["pm_material_id"], unique=False)
    op.create_index(op.f("ix_pm_overrides_updated_by_user_id"), "pm_overrides", ["updated_by_user_id"], unique=False)

    # 7. Create planning_readiness_scores table
    op.create_table(
        "planning_readiness_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), server_default=sa.text("100.0"), nullable=False),
        sa.Column("missing_masters_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_parameters_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("details_json", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_planning_readiness_scores_id"), "planning_readiness_scores", ["id"], unique=False)
    op.create_index(op.f("ix_planning_readiness_scores_plant_id"), "planning_readiness_scores", ["plant_id"], unique=False)

    # 8. Create procurement_recommendations table
    op.create_table(
        "procurement_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("recommended_qty", sa.Float(), nullable=False),
        sa.Column("recommended_vendor_id", sa.Integer(), nullable=True),
        sa.Column("dispatch_date", sa.Date(), nullable=True),
        sa.Column("expected_arrival_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=20), server_default=sa.text("'MEDIUM'"), nullable=False),
        sa.Column("planning_mode", sa.String(length=20), server_default=sa.text("'PROACTIVE'"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'RECOMMENDED'"), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(["recommended_vendor_id"], ["vendors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_procurement_recommendations_id"), "procurement_recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_procurement_recommendations_material_id"), "procurement_recommendations", ["material_id"], unique=False)
    op.create_index(op.f("ix_procurement_recommendations_plant_id"), "procurement_recommendations", ["plant_id"], unique=False)
    op.create_index(op.f("ix_procurement_recommendations_recommended_vendor_id"), "procurement_recommendations", ["recommended_vendor_id"], unique=False)
    op.create_index(op.f("ix_procurement_recommendations_status"), "procurement_recommendations", ["status"], unique=False)

    # 9. Create production_readiness_records table
    op.create_table(
        "production_readiness_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("fg_material_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'READY_TO_PRODUCE'"), nullable=False),
        sa.Column("blocking_rm_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("blocking_pm_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("details_json", sa.String(length=2000), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["fg_material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_readiness_records_fg_material_id"), "production_readiness_records", ["fg_material_id"], unique=False)
    op.create_index(op.f("ix_production_readiness_records_id"), "production_readiness_records", ["id"], unique=False)
    op.create_index(op.f("ix_production_readiness_records_plant_id"), "production_readiness_records", ["plant_id"], unique=False)
    op.create_index(op.f("ix_production_readiness_records_status"), "production_readiness_records", ["status"], unique=False)

    # 10. Create simulation_runs table
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scenario_name", sa.String(length=100), nullable=False),
        sa.Column("input_params_json", sa.String(length=4000), nullable=False),
        sa.Column("results_json", sa.String(length=4000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_simulation_runs_id"), "simulation_runs", ["id"], unique=False)
    op.create_index(op.f("ix_simulation_runs_user_id"), "simulation_runs", ["user_id"], unique=False)


def downgrade() -> None:
    # 10. Drop simulation_runs
    op.drop_index(op.f("ix_simulation_runs_user_id"), table_name="simulation_runs")
    op.drop_index(op.f("ix_simulation_runs_id"), table_name="simulation_runs")
    op.drop_table("simulation_runs")

    # 9. Drop production_readiness_records
    op.drop_index(op.f("ix_production_readiness_records_status"), table_name="production_readiness_records")
    op.drop_index(op.f("ix_production_readiness_records_plant_id"), table_name="production_readiness_records")
    op.drop_index(op.f("ix_production_readiness_records_fg_material_id"), table_name="production_readiness_records")
    op.drop_index(op.f("ix_production_readiness_records_id"), table_name="production_readiness_records")
    op.drop_table("production_readiness_records")

    # 8. Drop procurement_recommendations
    op.drop_index(op.f("ix_procurement_recommendations_status"), table_name="procurement_recommendations")
    op.drop_index(op.f("ix_procurement_recommendations_recommended_vendor_id"), table_name="procurement_recommendations")
    op.drop_index(op.f("ix_procurement_recommendations_plant_id"), table_name="procurement_recommendations")
    op.drop_index(op.f("ix_procurement_recommendations_material_id"), table_name="procurement_recommendations")
    op.drop_index(op.f("ix_procurement_recommendations_id"), table_name="procurement_recommendations")
    op.drop_table("procurement_recommendations")

    # 7. Drop planning_readiness_scores
    op.drop_index(op.f("ix_planning_readiness_scores_plant_id"), table_name="planning_readiness_scores")
    op.drop_index(op.f("ix_planning_readiness_scores_id"), table_name="planning_readiness_scores")
    op.drop_table("planning_readiness_scores")

    # 6. Drop pm_overrides
    op.drop_index(op.f("ix_pm_overrides_updated_by_user_id"), table_name="pm_overrides")
    op.drop_index(op.f("ix_pm_overrides_pm_material_id"), table_name="pm_overrides")
    op.drop_index(op.f("ix_pm_overrides_plant_id"), table_name="pm_overrides")
    op.drop_index(op.f("ix_pm_overrides_id"), table_name="pm_overrides")
    op.drop_index(op.f("ix_pm_overrides_fg_material_id"), table_name="pm_overrides")
    op.drop_table("pm_overrides")

    # 5. Drop rm_totality_mappings
    op.drop_index(op.f("ix_rm_totality_mappings_rm_material_id"), table_name="rm_totality_mappings")
    op.drop_index(op.f("ix_rm_totality_mappings_plant_id"), table_name="rm_totality_mappings")
    op.drop_index(op.f("ix_rm_totality_mappings_id"), table_name="rm_totality_mappings")
    op.drop_index(op.f("ix_rm_totality_mappings_fg_group_name"), table_name="rm_totality_mappings")
    op.drop_table("rm_totality_mappings")

    # 4. Remove columns from allocations
    op.drop_column("allocations", "expected_arrival_date")
    op.drop_column("allocations", "dispatch_date")
    op.drop_column("allocations", "recommendation_reason")
    op.drop_column("allocations", "proactive_flag")
    op.drop_column("allocations", "vehicle_capacity_used")

    # 3. Remove columns from plant_materials
    op.drop_column("plant_materials", "trigger_2")
    op.drop_column("plant_materials", "trigger_1")
    op.drop_column("plant_materials", "safety_stock_2")
    op.drop_column("plant_materials", "safety_stock_1")
    op.drop_column("plant_materials", "lead_time_2")
    op.drop_column("plant_materials", "lead_time_1")

    # 2. Remove columns from vendors
    op.drop_column("vendors", "lead_time_2_days")
    op.drop_column("vendors", "lead_time_1_days")
    op.drop_column("vendors", "capacity_per_day")

    # 1. Remove columns from materials
    op.drop_column("materials", "storage_capacity_limit")
    op.drop_column("materials", "material_group")
