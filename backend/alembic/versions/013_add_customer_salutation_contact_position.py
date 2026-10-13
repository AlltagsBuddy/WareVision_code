"""Anrede und Ansprechpartner-Position bei Kunden hinzufügen."""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Anrede (Herr/Frau/Divers/keine)
    bind.execute(sa.text(
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS salutation VARCHAR(20)"
    ))

    # Position/Funktion des Ansprechpartners (z.B. Geschäftsführer)
    bind.execute(sa.text(
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS contact_position VARCHAR(100)"
    ))


def downgrade() -> None:
    op.drop_column("customers", "contact_position")
    op.drop_column("customers", "salutation")
