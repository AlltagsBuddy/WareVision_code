"""DATEV-Export: Personenkonten-Zuordnung und Gutschrift-Kennzeichen für Eingangsrechnungen."""

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabelle und Spalte anlegen (idempotent), bestehende importierte Gutschriften kennzeichnen."""
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS datev_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kind VARCHAR(10) NOT NULL,
            ref_key VARCHAR(300) NOT NULL,
            name VARCHAR(255) NOT NULL,
            account_number INTEGER NOT NULL UNIQUE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_datev_accounts_kind_ref UNIQUE (kind, ref_key)
        )
    """))
    bind.execute(sa.text(
        "ALTER TABLE incoming_invoices ADD COLUMN IF NOT EXISTS is_credit_note BOOLEAN NOT NULL DEFAULT false"
    ))
    bind.execute(sa.text(
        "UPDATE incoming_invoices SET is_credit_note = true "
        "WHERE is_credit_note = false AND notes LIKE '%Gutschrift / Rechnungskorrektur%'"
    ))


def downgrade() -> None:
    """Tabelle und Spalte entfernen."""
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE incoming_invoices DROP COLUMN IF EXISTS is_credit_note"))
    bind.execute(sa.text("DROP TABLE IF EXISTS datev_accounts"))
