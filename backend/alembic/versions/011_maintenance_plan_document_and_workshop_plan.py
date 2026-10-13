"""Wartungsplan-Dokument und Wartungsplan am Werkstattauftrag."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dokument-Verknüpfung am Wartungsplan (1:1, nullable)
    op.add_column(
        "maintenance_plans",
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
    )

    # Wartungsplan am Werkstattauftrag (nullable, wird beim Erstellen automatisch gesetzt)
    op.add_column(
        "workshop_orders",
        sa.Column("maintenance_plan_id", UUID(as_uuid=True), sa.ForeignKey("maintenance_plans.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_index("ix_maintenance_plans_document_id", "maintenance_plans", ["document_id"])
    op.create_index("ix_workshop_orders_maintenance_plan_id", "workshop_orders", ["maintenance_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_workshop_orders_maintenance_plan_id", "workshop_orders")
    op.drop_index("ix_maintenance_plans_document_id", "maintenance_plans")
    op.drop_column("workshop_orders", "maintenance_plan_id")
    op.drop_column("maintenance_plans", "document_id")
