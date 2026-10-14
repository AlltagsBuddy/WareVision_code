"""Bestellwesen: Bestellungen, Positionen, Zielbestand und Lieferanten-Artikelnummer."""

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabellen und Spalten anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS target_stock INTEGER"))
    bind.execute(sa.text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS supplier_article_number VARCHAR(100)"))
    bind.execute(sa.text("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS customer_number VARCHAR(100)"))
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_number VARCHAR(50) NOT NULL UNIQUE,
            supplier_id UUID NOT NULL REFERENCES suppliers(id),
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            order_date DATE NOT NULL,
            expected_date DATE,
            notes TEXT,
            internal_notes TEXT,
            net_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            gross_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            sent_at TIMESTAMPTZ,
            sent_to_email VARCHAR(255),
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 1,
            article_id UUID REFERENCES articles(id),
            description TEXT NOT NULL,
            article_number VARCHAR(100),
            supplier_article_number VARCHAR(100),
            quantity INTEGER NOT NULL DEFAULT 1,
            received_quantity INTEGER NOT NULL DEFAULT 0,
            unit VARCHAR(50),
            unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
            vat_rate NUMERIC(5,2) NOT NULL DEFAULT 19.00,
            line_total_net NUMERIC(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_purchase_orders_supplier ON purchase_orders (supplier_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_purchase_orders_status ON purchase_orders (status)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_purchase_order_items_order ON purchase_order_items (purchase_order_id)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_purchase_order_items_article ON purchase_order_items (article_id)"))


def downgrade() -> None:
    """Tabellen und Spalten entfernen."""
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS purchase_order_items"))
    bind.execute(sa.text("DROP TABLE IF EXISTS purchase_orders"))
    bind.execute(sa.text("ALTER TABLE suppliers DROP COLUMN IF EXISTS customer_number"))
    bind.execute(sa.text("ALTER TABLE articles DROP COLUMN IF EXISTS supplier_article_number"))
    bind.execute(sa.text("ALTER TABLE articles DROP COLUMN IF EXISTS target_stock"))
