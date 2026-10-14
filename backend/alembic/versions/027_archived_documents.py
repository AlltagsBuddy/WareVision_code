"""Belegarchiv: unveränderbare Originale ausgegebener Dokumente (GoBD)."""

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Tabelle anlegen (idempotent)."""
    bind = op.get_bind()
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(30) NOT NULL,
            entity_id UUID NOT NULL,
            kind VARCHAR(30) NOT NULL,
            document_number VARCHAR(100) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            sha256 VARCHAR(64) NOT NULL,
            size_bytes INTEGER NOT NULL,
            backfilled BOOLEAN NOT NULL DEFAULT false,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_archived_documents_entity_kind UNIQUE (entity_type, entity_id, kind)
        )
    """))
    bind.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_archived_documents_entity ON archived_documents (entity_type, entity_id)"
    ))


def downgrade() -> None:
    """Tabelle entfernen (die Dateien im Archivordner bleiben erhalten)."""
    op.get_bind().execute(sa.text("DROP TABLE IF EXISTS archived_documents"))
