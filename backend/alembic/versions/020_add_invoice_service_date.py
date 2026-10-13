"""Leistungsdatum (service_date) für Rechnungen – § 14 Abs. 4 Nr. 6 UStG."""

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Spalte service_date anlegen (idempotent)."""
    op.get_bind().execute(sa.text(
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS service_date DATE"
    ))


def downgrade() -> None:
    """Spalte service_date entfernen."""
    op.get_bind().execute(sa.text(
        "ALTER TABLE invoices DROP COLUMN IF EXISTS service_date"
    ))
