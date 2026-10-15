"""Users API (admin only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role
from app.schemas.user import DEFAULT_PERMISSIONS, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _user_to_read(user: User) -> dict:
    """Benutzer in lesbares Dict umwandeln. Admins erhalten immer alle Rechte."""
    permissions = user.permissions if user.permissions is not None else DEFAULT_PERMISSIONS.copy()
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role_id": user.role_id,
        "role_name": user.role.name,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "permissions": permissions,
        "totp_enabled": bool(user.totp_enabled),
    }


@router.get("/roles")
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> list[dict]:
    """List roles for user creation (admin only)."""
    roles = db.query(Role).order_by(Role.name).all()
    return [{"id": str(r.id), "name": r.name, "description": r.description} for r in roles]


@router.get("", response_model=list[UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[dict]:
    """List users (admin only)."""
    users = db.query(User).order_by(User.email).offset(skip).limit(limit).all()
    return [_user_to_read(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Create user (admin only)."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Benutzer mit dieser E-Mail existiert bereits",
        )
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rolle nicht gefunden")

    user = User(
        role_id=payload.role_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        permissions=payload.permissions if payload.permissions is not None else DEFAULT_PERMISSIONS.copy(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_read(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")

    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = get_password_hash(data.pop("password"))
    if "email" in data:
        new_email = (data.pop("email") or "").strip().lower()
        if new_email and new_email != user.email:
            existing = db.query(User).filter(User.email == new_email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Benutzer mit dieser E-Mail existiert bereits",
                )
            user.email = new_email
    if "role_id" in data:
        role = db.query(Role).filter(Role.id == data["role_id"]).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rolle nicht gefunden")
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return _user_to_read(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Deactivate user (admin only). Cannot deactivate self."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sie können sich nicht selbst deaktivieren",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    user.is_active = False
    db.commit()


@router.post("/{user_id}/reset-2fa", response_model=UserRead)
def reset_two_factor(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Zwei-Faktor eines Benutzers zurücksetzen (z. B. Handy verloren). Bei der nächsten Anmeldung
    richtet er sie neu ein."""
    from app.services.audit import log_audit

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_pending_secret = None
    user.totp_last_counter = None
    user.totp_enabled_at = None
    user.recovery_codes = None
    log_audit(db, user_id=current_user.id, entity_type="user", entity_id=user.id, action="2fa_reset",
              new_values={"email": user.email})
    db.commit()
    db.refresh(user)
    return _user_to_read(user)
