"""Zwei-Faktor-Anmeldung (TOTP, RFC 6238) mit Wiederherstellungscodes.

- Das TOTP-Geheimnis wird verschlüsselt gespeichert (Schlüssel aus SECRET_KEY abgeleitet).
- Ein Code kann nur einmal verwendet werden (Schutz gegen Wiederverwendung).
- Wiederherstellungscodes werden nur als Hash gespeichert und sind einmalig gültig.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings

ISSUER = "WareVision"
RECOVERY_CODE_COUNT = 10
CHALLENGE_MINUTES = 10


class TwoFactorError(Exception):
    """Gespeichertes Geheimnis kann nicht gelesen werden (z. B. SECRET_KEY geändert)."""


def _fernet() -> Fernet:
    key = hashlib.sha256(("warevision-2fa:" + get_settings().SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise TwoFactorError("2FA-Geheimnis nicht lesbar") from exc


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=ISSUER)


def qr_data_uri(uri: str) -> str:
    """QR-Code als SVG-Bild (data:-Adresse) – wird hier erzeugt, kein externer Dienst."""
    return segno.make(uri, error="m").svg_data_uri(scale=5, dark="#000000", light="#ffffff", border=2)


def _normalize_code(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isdigit())


def verify_totp(secret: str, code: str, last_counter: int | None) -> int | None:
    """Code prüfen (±1 Zeitfenster à 30 s). Gibt den verwendeten Zähler zurück oder None.

    Ein Zähler, der nicht größer als last_counter ist, wird abgelehnt (keine Wiederverwendung).
    """
    digits = _normalize_code(code)
    if len(digits) != 6:
        return None
    totp = pyotp.TOTP(secret)
    now = datetime.now(timezone.utc)
    current = totp.timecode(now)
    for offset in (0, -1, 1):
        counter = current + offset
        if last_counter is not None and counter <= last_counter:
            continue
        if hmac.compare_digest(totp.generate_otp(counter), digits):
            return counter
    return None


# ---------------------------------------------------------------------------
# Wiederherstellungscodes
# ---------------------------------------------------------------------------

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ohne leicht verwechselbare Zeichen


def _hash_recovery(code: str) -> str:
    clean = "".join(ch for ch in code.upper() if ch.isalnum())
    return hashlib.sha256(("warevision-recovery:" + clean).encode()).hexdigest()


def new_recovery_codes() -> tuple[list[str], list[str]]:
    """(Klartext für die einmalige Anzeige, Hashes zum Speichern)."""
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes, [_hash_recovery(c) for c in codes]


def use_recovery_code(hashes: list[str] | None, code: str) -> list[str] | None:
    """Passt der Code, wird die neue Liste (ohne diesen Code) zurückgegeben, sonst None."""
    if not hashes or not code:
        return None
    h = _hash_recovery(code)
    for stored in hashes:
        if hmac.compare_digest(stored, h):
            return [x for x in hashes if x != stored]
    return None


# ---------------------------------------------------------------------------
# Kurzlebige Anmelde-Zwischentokens (nach Passwort, vor 2FA)
# ---------------------------------------------------------------------------

def create_challenge(user_id: str, purpose: str) -> str:
    """purpose: "2fa" (Code eingeben) oder "2fa_setup" (2FA einrichten)."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=CHALLENGE_MINUTES),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def read_challenge(token: str, purposes: tuple[str, ...]) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") not in purposes:
        return None
    return payload.get("sub")
