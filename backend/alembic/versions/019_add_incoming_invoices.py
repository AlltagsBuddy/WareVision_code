"""Eingangsrechnungen-Tabelle anlegen."""

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS incoming_invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_name VARCHAR(255) NOT NULL,
            invoice_number VARCHAR(100) NOT NULL,
            invoice_date DATE NOT NULL,
            due_date DATE,
            net_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            gross_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_rate NUMERIC(5,2) NOT NULL DEFAULT 19.00,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            category VARCHAR(100),
            notes TEXT,
            pdf_path TEXT,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_incoming_invoices_date ON incoming_invoices(invoice_date)"
    ))


def downgrade() -> None:
    op.drop_table("incoming_invoices")
