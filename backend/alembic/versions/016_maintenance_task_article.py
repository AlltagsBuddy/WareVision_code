"""Wartungsplan-Aufgaben: Artikel, Menge und Einheit hinzufügen."""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        ALTER TABLE maintenance_tasks
        ADD COLUMN IF NOT EXISTS article_id UUID
            REFERENCES articles(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS quantity NUMERIC(10,2) NOT NULL DEFAULT 1,
        ADD COLUMN IF NOT EXISTS unit VARCHAR(50)
    """))


def downgrade() -> None:
    op.drop_column("maintenance_tasks", "unit")
    op.drop_column("maintenance_tasks", "quantity")
    op.drop_column("maintenance_tasks", "article_id")
