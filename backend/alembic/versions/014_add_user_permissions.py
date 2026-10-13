"""Benutzer-Berechtigungen (Modul sichtbar/schreiben) als JSONB."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None

# Standardberechtigungen: alle Module sichtbar und schreibbar
DEFAULT_PERMISSIONS = {
    "customers": {"visible": True, "write": True},
    "vehicles": {"visible": True, "write": True},
    "articles": {"visible": True, "write": True},
    "suppliers": {"visible": True, "write": True},
    "stock": {"visible": True, "write": True},
    "workshop_orders": {"visible": True, "write": True},
    "maintenance_plans": {"visible": True, "write": True},
    "appointments": {"visible": True, "write": True},
    "invoices": {"visible": True, "write": True},
    "documents": {"visible": True, "write": True},
}


def upgrade() -> None:
    bind = op.get_bind()
    import json

    bind.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSONB"
    ))
    # Bestehende Benutzer erhalten Standardberechtigungen
    bind.execute(sa.text(
        f"UPDATE users SET permissions = '{json.dumps(DEFAULT_PERMISSIONS)}'::jsonb WHERE permissions IS NULL"
    ))


def downgrade() -> None:
    op.drop_column("users", "permissions")
