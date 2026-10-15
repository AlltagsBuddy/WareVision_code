"""Zwei-Faktor-Anmeldung (TOTP) für Benutzer."""

import sqlalchemy as sa
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Spalten anlegen (idempotent)."""
    bind = op.get_bind()
    for stmt in (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_pending_secret TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_last_counter BIGINT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled_at TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_codes JSONB",
    ):
        bind.execute(sa.text(stmt))


def downgrade() -> None:
    bind = op.get_bind()
    for col in ("recovery_codes", "totp_enabled_at", "totp_last_counter", "totp_pending_secret", "totp_secret", "totp_enabled"):
        bind.execute(sa.text(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}"))
