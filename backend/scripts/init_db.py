"""Initialize database: create tables, seed roles and admin user."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models import Role, User


def init_roles_and_admin(db, reset_admin: bool = False):
    """Create default roles and admin user."""
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator")
        db.add(admin_role)
        db.flush()

    werkstatt_role = db.query(Role).filter(Role.name == "werkstatt").first()
    if not werkstatt_role:
        werkstatt_role = Role(name="werkstatt", description="Werkstatt")
        db.add(werkstatt_role)
        db.flush()

    for role_name, role_desc in [
        ("chef", "Chef/Chefin"),
        ("buero", "Büro"),
        ("mitarbeiter", "Mitarbeiter"),
    ]:
        if not db.query(Role).filter(Role.name == role_name).first():
            db.add(Role(name=role_name, description=role_desc))
    db.flush()

    import os

    from app.core.config import get_settings

    if get_settings().is_production:
        # Auf dem Server nie ein Konto mit Standardpasswort anlegen
        if reset_admin:
            print("--reset-admin ist auf dem Server gesperrt. Bitte scripts/manage_user.py set-password verwenden.")
        has_admin = db.query(User).filter(User.role_id == admin_role.id).first() is not None
        email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not has_admin and email and len(password) >= 10:
            db.add(User(role_id=admin_role.id, first_name="Admin", last_name="WareVision",
                        email=email, password_hash=get_password_hash(password)))
            print(f"Admin {email} angelegt.")
        elif not has_admin:
            print("Kein Admin vorhanden. ADMIN_EMAIL und ADMIN_PASSWORD (mind. 10 Zeichen) setzen "
                  "oder Daten vom PC übernehmen.")
        db.commit()
        print("Rollen geprüft.")
        return

    admin_user = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not admin_user:
        admin_user = User(
            role_id=admin_role.id,
            first_name="Admin",
            last_name="WareVision",
            email="admin@warevision.local",
            password_hash=get_password_hash("admin123"),
        )
        db.add(admin_user)
    elif reset_admin:
        admin_user.password_hash = get_password_hash("admin123")
        admin_user.is_active = True
        print("Admin-Passwort auf admin123 zurückgesetzt.")

    db.commit()
    print("Roles and admin user created.")
    print("Login: admin@warevision.local / admin123")


def main():
    """Run init."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset-admin",
        action="store_true",
        help="Admin-Passwort auf admin123 zurücksetzen (falls Login nicht funktioniert)",
    )
    args = parser.parse_args()

    from app.core.database import Base, init_db

    init_db()  # Registriert alle Models bei Base.metadata
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        init_roles_and_admin(db, reset_admin=args.reset_admin)
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
