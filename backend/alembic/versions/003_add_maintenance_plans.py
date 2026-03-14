"""Add maintenance_plans and maintenance_tasks tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manufacturer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("interval_km", sa.Integer(), nullable=True),
        sa.Column("interval_hours", sa.Integer(), nullable=True),
        sa.Column("interval_months", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_model_id"], ["vehicle_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_plans_manufacturer_id", "maintenance_plans", ["manufacturer_id"])
    op.create_index("ix_maintenance_plans_vehicle_model_id", "maintenance_plans", ["vehicle_model_id"])

    op.create_table(
        "maintenance_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("maintenance_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["maintenance_plan_id"], ["maintenance_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_tasks_maintenance_plan_id", "maintenance_tasks", ["maintenance_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_maintenance_tasks_maintenance_plan_id", table_name="maintenance_tasks")
    op.drop_table("maintenance_tasks")
    op.drop_index("ix_maintenance_plans_vehicle_model_id", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_manufacturer_id", table_name="maintenance_plans")
    op.drop_table("maintenance_plans")
