"""EK/VK bei Fahrzeugen + Artikel-Fahrzeugmodell-Kompatibilitätstabelle."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Fahrzeuge: EK (Einkaufspreis) und VK (Verkaufspreis) – IF NOT EXISTS
    bind.execute(sa.text(
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(10,2)"
    ))
    bind.execute(sa.text(
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS sale_price NUMERIC(10,2)"
    ))

    # Artikel ↔ Fahrzeugmodell Kompatibilitätstabelle (many-to-many) – IF NOT EXISTS
    bind.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS article_vehicle_models (
            article_id  UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            vehicle_model_id UUID NOT NULL REFERENCES vehicle_models(id) ON DELETE CASCADE,
            PRIMARY KEY (article_id, vehicle_model_id)
        )
    """))
    bind.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_article_vehicle_models_article_id
            ON article_vehicle_models (article_id)
    """))
    bind.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_article_vehicle_models_vehicle_model_id
            ON article_vehicle_models (vehicle_model_id)
    """))


def downgrade() -> None:
    op.drop_index("ix_article_vehicle_models_vehicle_model_id", "article_vehicle_models")
    op.drop_index("ix_article_vehicle_models_article_id", "article_vehicle_models")
    op.drop_table("article_vehicle_models")
    op.drop_column("vehicles", "sale_price")
    op.drop_column("vehicles", "purchase_price")
