"""Stornorechnung-Felder für GoBD-konforme Rechnungsstornierung."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("cancellation_of_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("cancellation_invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "cancellation_invoice_id")
    op.drop_column("invoices", "cancellation_of_id")
