"""Lagerorte-Tabelle und FK-Spalten für Artikel und Fahrzeuge."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS storage_locations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    bind.execute(sa.text("""
        ALTER TABLE articles
        ADD COLUMN IF NOT EXISTS storage_location_id UUID
        REFERENCES storage_locations(id) ON DELETE SET NULL
    """))

    bind.execute(sa.text("""
        ALTER TABLE vehicles
        ADD COLUMN IF NOT EXISTS storage_location_id UUID
        REFERENCES storage_locations(id) ON DELETE SET NULL
    """))


def downgrade() -> None:
    op.drop_column("vehicles", "storage_location_id")
    op.drop_column("articles", "storage_location_id")
    op.drop_table("storage_locations")
