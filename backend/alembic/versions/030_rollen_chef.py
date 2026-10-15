"""Fünf Rollen: Admin, Chef/Chefin, Büro, Werkstatt, Mitarbeiter (Geschäftsführung → Chef/Chefin)."""

import sqlalchemy as sa
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None

ROLES = [
    ("admin", "Administrator"),
    ("chef", "Chef/Chefin"),
    ("buero", "Büro"),
    ("werkstatt", "Werkstatt"),
    ("mitarbeiter", "Mitarbeiter"),
]


def upgrade() -> None:
    """Idempotent: Rolle umbenennen bzw. zusammenführen, fehlende Rollen anlegen."""
    bind = op.get_bind()
    gf = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'geschaeftsfuehrung'")).scalar()
    chef = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'chef'")).scalar()
    if gf and not chef:
        bind.execute(sa.text("UPDATE roles SET name = 'chef' WHERE id = :id"), {"id": gf})
    elif gf and chef:
        bind.execute(sa.text("UPDATE users SET role_id = :chef WHERE role_id = :gf"), {"chef": chef, "gf": gf})
        bind.execute(sa.text("DELETE FROM roles WHERE id = :id"), {"id": gf})
    for name, desc in ROLES:
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, name, description, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :n, :d, now(), now()) ON CONFLICT (name) DO NOTHING"
            ),
            {"n": name, "d": desc},
        )
        bind.execute(sa.text("UPDATE roles SET description = :d WHERE name = :n"), {"n": name, "d": desc})
    # Leitung braucht keine Einzelrechte
    bind.execute(sa.text(
        "UPDATE users SET permissions = NULL WHERE role_id IN (SELECT id FROM roles WHERE name IN ('admin', 'chef'))"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE roles SET name = 'geschaeftsfuehrung' WHERE name = 'chef'"))
