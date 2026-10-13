"""Eingangsrechnungen: Felder für importierte E-Rechnungen (Original-Archiv, GoBD)."""

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

COLUMNS = [
    ("einvoice_format", "VARCHAR(30)"),
    ("original_path", "TEXT"),
    ("original_filename", "VARCHAR(255)"),
    ("original_sha256", "VARCHAR(64)"),
    ("service_date", "DATE"),
    ("supplier_vat_id", "VARCHAR(50)"),
]


def upgrade() -> None:
    """Spalten anlegen (idempotent)."""
    bind = op.get_bind()
    for name, sql_type in COLUMNS:
        bind.execute(sa.text(f"ALTER TABLE incoming_invoices ADD COLUMN IF NOT EXISTS {name} {sql_type}"))


def downgrade() -> None:
    """Spalten entfernen."""
    bind = op.get_bind()
    for name, _ in COLUMNS:
        bind.execute(sa.text(f"ALTER TABLE incoming_invoices DROP COLUMN IF EXISTS {name}"))
