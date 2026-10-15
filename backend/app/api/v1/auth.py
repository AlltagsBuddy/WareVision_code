"""Auth API."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.core.config import get_settings
from app.schemas.auth import (
    MIN_PASSWORD_LENGTH,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TwoFactorCodeRequest,
    TwoFactorConfirmRequest,
    TwoFactorConfirmResponse,
    TwoFactorSetupRequest,
    TwoFactorSetupStart,
    TwoFactorStatus,
    TwoFactorVerifyRequest,
    UserResponse,
)
from app.services import two_factor as tf

router = APIRouter(prefix="/auth", tags=["auth"])


# Bekannte Standardpasswörter – auf dem Server gesperrt
DEFAULT_PASSWORDS = ("admin123",)


def _client_info(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


def _finish_login(db: Session, user: User, request: Request, method: str) -> str:
    """Anmeldung abschließen: Zeitpunkt setzen, protokollieren, Zugangstoken ausgeben."""
    from app.services.audit import log_audit

    ip, ua = _client_info(request)
    user.last_login_at = datetime.now(timezone.utc)
    log_audit(db, user_id=user.id, entity_type="user", entity_id=user.id, action="login",
              new_values={"email": user.email, "method": method}, ip_address=ip, user_agent=ua)
    db.commit()
    return create_access_token(subject=user.id)


def _audit_failed(db: Session, user: User, request: Request, reason: str) -> None:
    from app.services.audit import log_audit

    ip, ua = _client_info(request)
    log_audit(db, user_id=user.id, entity_type="user", entity_id=user.id, action="login_failed",
              new_values={"email": user.email, "reason": reason}, ip_address=ip, user_agent=ua)
    db.commit()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Anmeldung mit E-Mail und Passwort (danach ggf. Zwei-Faktor-Code)."""
    from app.services.audit import log_audit

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            log_audit(
                db,
                user_id=user.id,
                entity_type="user",
                entity_id=user.id,
                action="login_failed",
                new_values={"email": user.email, "reason": "Falsches Passwort"},
                ip_address=ip,
                user_agent=ua,
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige E-Mail oder Passwort",
        )
    if not user.is_active:
        log_audit(
            db,
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            action="login_failed",
            new_values={"email": user.email, "reason": "Konto deaktiviert"},
            ip_address=ip,
            user_agent=ua,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer ist deaktiviert",
        )

    settings = get_settings()
    if settings.is_production and any(verify_password(p, user.password_hash) for p in DEFAULT_PASSWORDS):
        _audit_failed(db, user, request, "Standardpasswort auf dem Server gesperrt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dieses Konto hat noch das Standardpasswort und ist auf dem Server gesperrt. "
                   "Bitte das Passwort per Befehl neu setzen (siehe Anleitung Server).",
        )

    # Zwei-Faktor-Anmeldung: erst nach dem Code gibt es ein Zugangstoken
    if user.totp_enabled:
        return LoginResponse(two_factor_required=True, challenge_token=tf.create_challenge(str(user.id), "2fa"))
    if settings.two_factor_required:
        return LoginResponse(two_factor_setup_required=True,
                             challenge_token=tf.create_challenge(str(user.id), "2fa_setup"))

    return LoginResponse(access_token=_finish_login(db, user, request, "password"))


def _user_from_challenge(db: Session, token: str, purposes: tuple[str, ...]) -> User:
    user_id = tf.read_challenge(token, purposes)
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Anmeldung abgelaufen – bitte erneut mit Passwort anmelden")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Benutzer ist deaktiviert")
    return user


def _check_code(db: Session, user: User, code: str | None) -> bool:
    """TOTP-Code prüfen und Zähler merken (jeder Code nur einmal gültig)."""
    if not code or not user.totp_secret:
        return False
    try:
        secret = tf.decrypt_secret(user.totp_secret)
    except tf.TwoFactorError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Die Zwei-Faktor-Einrichtung dieses Kontos ist nicht mehr lesbar. "
                   "Ein Admin muss sie zurücksetzen.",
        )
    counter = tf.verify_totp(secret, code, user.totp_last_counter)
    if counter is None:
        return False
    user.totp_last_counter = counter
    return True


@router.post("/2fa/verify", response_model=LoginResponse)
@limiter.limit("10/minute")
def verify_two_factor(
    payload: TwoFactorVerifyRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Zweiter Schritt der Anmeldung: Code aus der App oder ein Wiederherstellungscode."""
    from app.services.audit import log_audit

    user = _user_from_challenge(db, payload.challenge_token, ("2fa",))
    if not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zwei-Faktor ist nicht eingerichtet")
    if payload.recovery_code:
        remaining = tf.use_recovery_code(user.recovery_codes, payload.recovery_code)
        if remaining is None:
            _audit_failed(db, user, request, "Falscher Wiederherstellungscode")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wiederherstellungscode ungültig")
        user.recovery_codes = remaining
        ip, ua = _client_info(request)
        log_audit(db, user_id=user.id, entity_type="user", entity_id=user.id, action="2fa_recovery_code_used",
                  new_values={"remaining": len(remaining)}, ip_address=ip, user_agent=ua)
        return LoginResponse(access_token=_finish_login(db, user, request, "recovery_code"))
    if not _check_code(db, user, payload.code):
        _audit_failed(db, user, request, "Falscher 2FA-Code")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Code ist falsch oder abgelaufen. Bitte den aktuellen Code aus der App eingeben.")
    return LoginResponse(access_token=_finish_login(db, user, request, "2fa"))


@router.post("/2fa/setup/start", response_model=TwoFactorSetupStart)
@limiter.limit("10/minute")
def start_two_factor_setup(
    payload: TwoFactorSetupRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TwoFactorSetupStart:
    """Neues Geheimnis erzeugen und als QR-Code liefern (noch nicht aktiv)."""
    user = _user_from_challenge(db, payload.challenge_token, ("2fa_setup",))
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zwei-Faktor ist bereits eingerichtet")
    secret = tf.new_secret()
    user.totp_pending_secret = tf.encrypt_secret(secret)
    db.commit()
    uri = tf.provisioning_uri(secret, user.email)
    return TwoFactorSetupStart(secret=secret, otpauth_uri=uri, qr_data_uri=tf.qr_data_uri(uri), account=user.email)


@router.post("/2fa/setup/confirm", response_model=TwoFactorConfirmResponse)
@limiter.limit("10/minute")
def confirm_two_factor_setup(
    payload: TwoFactorConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TwoFactorConfirmResponse:
    """Ersten Code bestätigen: 2FA aktivieren, Wiederherstellungscodes ausgeben, anmelden."""
    from app.services.audit import log_audit

    user = _user_from_challenge(db, payload.challenge_token, ("2fa_setup",))
    if user.totp_enabled or not user.totp_pending_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bitte die Einrichtung neu starten")
    try:
        secret = tf.decrypt_secret(user.totp_pending_secret)
    except tf.TwoFactorError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bitte die Einrichtung neu starten")
    counter = tf.verify_totp(secret, payload.code, None)
    if counter is None:
        _audit_failed(db, user, request, "Falscher Code bei 2FA-Einrichtung")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Code ist falsch. Bitte den aktuellen 6-stelligen Code aus der App eingeben "
                                   "und prüfen, ob die Uhrzeit am Handy stimmt.")
    codes, hashes = tf.new_recovery_codes()
    user.totp_secret = tf.encrypt_secret(secret)
    user.totp_pending_secret = None
    user.totp_enabled = True
    user.totp_enabled_at = datetime.now(timezone.utc)
    user.totp_last_counter = counter
    user.recovery_codes = hashes
    ip, ua = _client_info(request)
    log_audit(db, user_id=user.id, entity_type="user", entity_id=user.id, action="2fa_enabled",
              ip_address=ip, user_agent=ua)
    token = _finish_login(db, user, request, "2fa_setup")
    return TwoFactorConfirmResponse(access_token=token, recovery_codes=codes)


@router.get("/2fa/status", response_model=TwoFactorStatus)
def two_factor_status(current_user: Annotated[User, Depends(get_current_user)]) -> TwoFactorStatus:
    return TwoFactorStatus(
        enabled=current_user.totp_enabled,
        required=get_settings().two_factor_required,
        enabled_at=current_user.totp_enabled_at.isoformat() if current_user.totp_enabled_at else None,
        recovery_codes_left=len(current_user.recovery_codes or []),
    )


@router.post("/2fa/recovery-codes", response_model=list[str])
@limiter.limit("5/minute")
def regenerate_recovery_codes(
    payload: TwoFactorCodeRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[str]:
    """Neue Wiederherstellungscodes (alte werden ungültig). Erfordert den aktuellen Code."""
    from app.services.audit import log_audit

    if not current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zwei-Faktor ist nicht eingerichtet")
    if not _check_code(db, current_user, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code ist falsch oder abgelaufen")
    codes, hashes = tf.new_recovery_codes()
    current_user.recovery_codes = hashes
    log_audit(db, user_id=current_user.id, entity_type="user", entity_id=current_user.id,
              action="2fa_recovery_codes_renewed")
    db.commit()
    return codes


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RegisterResponse:
    """Öffentliche Registrierung. Neuer Benutzer wird als inaktiv angelegt und muss von einem Admin freigeschaltet werden."""
    from app.models.role import Role

    if not get_settings().REGISTRATION_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registrierung ist deaktiviert")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ein Benutzer mit dieser E-Mail existiert bereits",
        )
    role = db.query(Role).filter(Role.name == "werkstatt").first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rolle 'werkstatt' nicht gefunden. Bitte init_db ausführen.",
        )
    user = User(
        email=payload.email,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        password_hash=get_password_hash(payload.password),
        role_id=role.id,
        is_active=False,  # Muss von Admin freigeschaltet werden
    )
    db.add(user)
    db.commit()
    return RegisterResponse(
        message="Registrierung erfolgreich. Ein Administrator muss Ihr Konto freischalten, bevor Sie sich anmelden können."
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current user info inklusive Modulberechtigungen."""
    from app.core.permissions import ROLE_LABELS, effective_permissions, is_manager

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role_name=current_user.role.name,
        role_label=ROLE_LABELS.get(current_user.role.name, current_user.role.name),
        is_manager=is_manager(current_user),
        is_active=current_user.is_active,
        permissions=effective_permissions(current_user),
    )


@router.get("/me/export")
def export_my_data(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """DSGVO Art. 15/20: Export own user data (Auskunftsrecht, Datenübertragbarkeit)."""
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role_name": current_user.role.name,
            "is_active": current_user.is_active,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        },
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Change own password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aktuelles Passwort ist falsch",
        )
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Neues Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben",
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Passwort geändert"}
