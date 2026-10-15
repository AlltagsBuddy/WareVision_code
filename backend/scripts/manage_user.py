"""Benutzer auf dem Server verwalten (ohne Weboberfläche).

Beispiele (im Ordner mit docker-compose.prod.yml):
  docker compose -f docker-compose.prod.yml exec backend python scripts/manage_user.py list
  docker compose -f docker-compose.prod.yml exec backend python scripts/manage_user.py set-password chef@firma.de
  docker compose -f docker-compose.prod.yml exec backend python scripts/manage_user.py reset-2fa chef@firma.de

Das Passwort wird verdeckt abgefragt und nicht angezeigt.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models import User  # noqa: E402
from app.schemas.auth import MIN_PASSWORD_LENGTH  # noqa: E402
from app.services.audit import log_audit  # noqa: E402


def _get_user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        sys.exit(f"Kein Benutzer mit der E-Mail {email}")
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="WareVision-Benutzer verwalten")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Benutzer anzeigen")
    p1 = sub.add_parser("set-password", help="Passwort neu setzen (wird verdeckt abgefragt)")
    p1.add_argument("email")
    p2 = sub.add_parser("reset-2fa", help="Zwei-Faktor zurücksetzen (bei nächster Anmeldung neu einrichten)")
    p2.add_argument("email")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.cmd == "list":
            for u in db.query(User).order_by(User.email).all():
                print(f"{u.email:40} {u.role.name:20} aktiv={'ja' if u.is_active else 'nein'} "
                      f"2FA={'ja' if u.totp_enabled else 'nein'}")
            return
        user = _get_user(db, args.email)
        if args.cmd == "set-password":
            pw1 = getpass.getpass("Neues Passwort: ")
            pw2 = getpass.getpass("Wiederholen: ")
            if pw1 != pw2:
                sys.exit("Die Passwörter stimmen nicht überein.")
            if len(pw1) < MIN_PASSWORD_LENGTH:
                sys.exit(f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen.")
            if pw1 in ("admin123",):
                sys.exit("Dieses Passwort ist nicht erlaubt.")
            user.password_hash = get_password_hash(pw1)
            user.is_active = True
            log_audit(db, user_id=None, entity_type="user", entity_id=user.id, action="password_set_cli",
                      new_values={"email": user.email})
            db.commit()
            print(f"Passwort für {user.email} gesetzt.")
        elif args.cmd == "reset-2fa":
            user.totp_enabled = False
            user.totp_secret = None
            user.totp_pending_secret = None
            user.totp_last_counter = None
            user.totp_enabled_at = None
            user.recovery_codes = None
            log_audit(db, user_id=None, entity_type="user", entity_id=user.id, action="2fa_reset_cli",
                      new_values={"email": user.email})
            db.commit()
            print(f"Zwei-Faktor für {user.email} zurückgesetzt. Bei der nächsten Anmeldung neu einrichten.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
