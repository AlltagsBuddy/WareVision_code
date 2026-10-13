"""Angebote / Kostenvoranschläge (quotes, quote_items)."""

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabellen anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS quotes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            quote_number VARCHAR(100) NOT NULL UNIQUE,
            quote_type VARCHAR(20) NOT NULL DEFAULT 'offer',
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            customer_id UUID NOT NULL REFERENCES customers(id),
            vehicle_id UUID REFERENCES vehicles(id),
            quote_date DATE NOT NULL,
            valid_until DATE,
            subject VARCHAR(255),
            notes TEXT,
            internal_notes TEXT,
            net_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            gross_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            previous_quote_id UUID REFERENCES quotes(id) ON DELETE SET NULL,
            workshop_order_id UUID REFERENCES workshop_orders(id) ON DELETE SET NULL,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS quote_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 1,
            item_type VARCHAR(20) NOT NULL,
            article_id UUID REFERENCES articles(id),
            description TEXT NOT NULL,
            quantity NUMERIC(10,2) NOT NULL DEFAULT 1,
            unit VARCHAR(50),
            unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_rate NUMERIC(5,2) NOT NULL DEFAULT 19.00,
            line_total_net NUMERIC(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_quotes_customer_id ON quotes (customer_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_quote_items_quote_id ON quote_items (quote_id)"))


def downgrade() -> None:
    """Tabellen entfernen."""
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS quote_items"))
    bind.execute(sa.text("DROP TABLE IF EXISTS quotes"))
