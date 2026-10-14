"""Rechnungskorrektur (Gutschrift des Verkäufers): Belegart, Bezug auf Originalrechnung und -position."""

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Spalten anlegen (idempotent) und bestehende Stornorechnungen kennzeichnen."""
    bind = op.get_bind()
    bind.execute(sa.text(
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS document_type VARCHAR(20) NOT NULL DEFAULT 'invoice'"
    ))
    bind.execute(sa.text(
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS corrects_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL"
    ))
    bind.execute(sa.text(
        "ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS corrects_item_id UUID REFERENCES invoice_items(id) ON DELETE SET NULL"
    ))
    bind.execute(sa.text(
        "ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS returned_to_stock BOOLEAN NOT NULL DEFAULT false"
    ))
    bind.execute(sa.text(
        "UPDATE invoices SET document_type = 'cancellation' "
        "WHERE cancellation_of_id IS NOT NULL AND document_type = 'invoice'"
    ))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_corrects ON invoices (corrects_invoice_id)"))


def downgrade() -> None:
    """Spalten entfernen."""
    bind = op.get_bind()
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_invoices_corrects"))
    bind.execute(sa.text("ALTER TABLE invoice_items DROP COLUMN IF EXISTS returned_to_stock"))
    bind.execute(sa.text("ALTER TABLE invoice_items DROP COLUMN IF EXISTS corrects_item_id"))
    bind.execute(sa.text("ALTER TABLE invoices DROP COLUMN IF EXISTS corrects_invoice_id"))
    bind.execute(sa.text("ALTER TABLE invoices DROP COLUMN IF EXISTS document_type"))
