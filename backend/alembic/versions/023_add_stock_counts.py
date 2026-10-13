"""Inventur (stock_counts, stock_count_items)."""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabellen anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS stock_counts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            count_number VARCHAR(50) NOT NULL UNIQUE,
            count_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            storage_location_id UUID REFERENCES storage_locations(id) ON DELETE SET NULL,
            category_id UUID REFERENCES article_categories(id) ON DELETE SET NULL,
            scope_label VARCHAR(255),
            notes TEXT,
            value_expected NUMERIC(14,2),
            value_counted NUMERIC(14,2),
            created_by UUID REFERENCES users(id),
            completed_by UUID REFERENCES users(id),
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS stock_count_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            stock_count_id UUID NOT NULL REFERENCES stock_counts(id) ON DELETE CASCADE,
            article_id UUID NOT NULL REFERENCES articles(id),
            article_number VARCHAR(100) NOT NULL,
            article_name VARCHAR(255) NOT NULL,
            location VARCHAR(255),
            barcode VARCHAR(255),
            unit_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
            sort_key VARCHAR(400) NOT NULL DEFAULT '',
            book_qty_at_start INTEGER NOT NULL DEFAULT 0,
            expected_qty INTEGER,
            counted_qty INTEGER,
            difference INTEGER,
            note VARCHAR(255),
            counted_by UUID REFERENCES users(id),
            counted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_stock_count_items_count ON stock_count_items (stock_count_id)"))


def downgrade() -> None:
    """Tabellen entfernen."""
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS stock_count_items"))
    bind.execute(sa.text("DROP TABLE IF EXISTS stock_counts"))
