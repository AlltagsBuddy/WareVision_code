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
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, RegisterResponse, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Login and get JWT token."""
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

    user.last_login_at = datetime.now(timezone.utc)
    log_audit(
        db,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action="login",
        new_values={"email": user.email},
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RegisterResponse:
    """Öffentliche Registrierung. Neuer Benutzer wird als inaktiv angelegt und muss von einem Admin freigeschaltet werden."""
    from app.models.role import Role

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
    from app.schemas.user import DEFAULT_PERMISSIONS

    permissions = current_user.permissions if current_user.permissions is not None else DEFAULT_PERMISSIONS.copy()
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role_name=current_user.role.name,
        is_active=current_user.is_active,
        permissions=permissions,
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
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neues Passwort muss mindestens 6 Zeichen haben",
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Passwort geändert"}
