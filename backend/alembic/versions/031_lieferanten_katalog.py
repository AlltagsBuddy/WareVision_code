"""Lieferanten-Artikeldaten (Katalog) für Vorschläge beim Anlegen per Barcode."""

import sqlalchemy as sa
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabelle anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS supplier_catalog_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
            supplier_name VARCHAR(255) NOT NULL,
            source VARCHAR(20) NOT NULL,
            source_ref VARCHAR(255),
            barcode VARCHAR(255),
            supplier_article_number VARCHAR(100),
            name VARCHAR(500) NOT NULL,
            description TEXT,
            manufacturer VARCHAR(150),
            manufacturer_part_number VARCHAR(100),
            purchase_price NUMERIC(12, 2),
            retail_price_net NUMERIC(12, 2),
            vat_rate NUMERIC(5, 2),
            unit VARCHAR(30),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_supplier_catalog_barcode ON supplier_catalog_items (barcode)"))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_supplier_catalog_supplier_number "
        "ON supplier_catalog_items (supplier_name, supplier_article_number)"
    ))


def downgrade() -> None:
    op.get_bind().execute(sa.text("DROP TABLE IF EXISTS supplier_catalog_items"))
