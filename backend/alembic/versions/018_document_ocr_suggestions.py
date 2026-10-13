"""OCR-Vorschlag-Spalten für Dokumente."""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS ocr_customer_id UUID
            REFERENCES customers(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS ocr_vehicle_id UUID
            REFERENCES vehicles(id) ON DELETE SET NULL
    """))


def downgrade() -> None:
    op.drop_column("documents", "ocr_vehicle_id")
    op.drop_column("documents", "ocr_customer_id")
