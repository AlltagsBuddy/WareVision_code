"""Wartungsplan-Baujahre, Teile-Hersteller beim Artikel, Fotos am Werkstattauftrag,
Auftragsposition nach Storno entfernbar (Verweis der Rechnungsposition wird geleert)."""

import sqlalchemy as sa
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Spalten und Tabelle anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE maintenance_plans ADD COLUMN IF NOT EXISTS build_year_from INTEGER"))
    bind.execute(sa.text("ALTER TABLE maintenance_plans ADD COLUMN IF NOT EXISTS build_year_to INTEGER"))
    bind.execute(sa.text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS part_manufacturer VARCHAR(150)"))
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS workshop_order_photos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workshop_order_id UUID NOT NULL REFERENCES workshop_orders(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            caption VARCHAR(255),
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    # Verweis Rechnungsposition → Auftragsposition: beim Entfernen der Auftragsposition leeren
    bind.execute(sa.text(
        "ALTER TABLE invoice_items DROP CONSTRAINT IF EXISTS invoice_items_workshop_order_item_id_fkey"
    ))
    bind.execute(sa.text(
        "ALTER TABLE invoice_items ADD CONSTRAINT invoice_items_workshop_order_item_id_fkey "
        "FOREIGN KEY (workshop_order_item_id) REFERENCES workshop_order_items(id) ON DELETE SET NULL"
    ))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_workshop_order_photos_order ON workshop_order_photos (workshop_order_id)"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS workshop_order_photos"))
    bind.execute(sa.text(
        "ALTER TABLE invoice_items DROP CONSTRAINT IF EXISTS invoice_items_workshop_order_item_id_fkey"
    ))
    bind.execute(sa.text(
        "ALTER TABLE invoice_items ADD CONSTRAINT invoice_items_workshop_order_item_id_fkey "
        "FOREIGN KEY (workshop_order_item_id) REFERENCES workshop_order_items(id)"
    ))
    bind.execute(sa.text("ALTER TABLE articles DROP COLUMN IF EXISTS part_manufacturer"))
    bind.execute(sa.text("ALTER TABLE maintenance_plans DROP COLUMN IF EXISTS build_year_to"))
    bind.execute(sa.text("ALTER TABLE maintenance_plans DROP COLUMN IF EXISTS build_year_from"))
