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
from app.core.permissions import (
    MANAGER_ROLES,
    MODULES,
    RIGHTS,
    ROLE_LABELS,
    ROLE_ORDER,
    ROLE_TEMPLATES,
    effective_permissions,
    is_manager,
    normalize_permissions,
)
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _audit_user(db: Session, actor: User, user: User, action: str, new: dict, old: dict | None = None) -> None:
    """Änderungen an Benutzern und Rechten nachvollziehbar protokollieren."""
    from app.services.audit import log_audit

    log_audit(db, user_id=actor.id, entity_type="user", entity_id=user.id, action=action,
              old_values=old, new_values={"email": user.email, **new})


def _user_to_read(user: User) -> dict:
    """Benutzer in lesbares Dict umwandeln. Admins erhalten immer alle Rechte."""
    permissions = effective_permissions(user)
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role_id": user.role_id,
        "role_name": user.role.name,
        "role_label": ROLE_LABELS.get(user.role.name, user.role.name),
        "is_manager": is_manager(user),
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
    """Rollen mit Bezeichnung und Vorlage für die Bereichs- und Sonderrechte."""
    roles = [r for r in db.query(Role).all() if r.name in ROLE_LABELS]
    roles.sort(key=lambda r: ROLE_ORDER.index(r.name))
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "label": ROLE_LABELS[r.name],
            "description": r.description,
            "is_manager": r.name in MANAGER_ROLES,
            "template": ROLE_TEMPLATES.get(r.name),
        }
        for r in roles
    ]


@router.get("/permission-catalog")
def permission_catalog(current_user: Annotated[User, Depends(require_admin)]) -> dict:
    """Bereiche und Sonderrechte mit Beschreibung (für die Benutzerverwaltung)."""
    return {
        "modules": [{"key": k, "label": v} for k, v in MODULES.items()],
        "rights": [{"key": k, "label": v} for k, v in RIGHTS.items()],
    }


def _active_managers(db: Session) -> list[User]:
    return [u for u in db.query(User).filter(User.is_active.is_(True)).all() if is_manager(u)]


def _ensure_manager_remains(db: Session, user: User, stays_manager: bool) -> None:
    """Mindestens ein aktiver Administrator oder Chef/Chefin muss bleiben."""
    if stays_manager or not (user.is_active and is_manager(user)):
        return
    others = [u for u in _active_managers(db) if u.id != user.id]
    if not others:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Es muss mindestens ein aktiver Administrator oder Chef/Chefin bleiben.")


def _permissions_for(role: Role, raw: dict | None) -> dict | None:
    """Leitung braucht keine Einzelrechte; sonst Eingabe bereinigen oder Vorlage der Rolle nehmen."""
    if role.name in MANAGER_ROLES:
        return None
    cleaned = normalize_permissions(raw)
    if cleaned is None:
        template = ROLE_TEMPLATES.get(role.name)
        cleaned = normalize_permissions(template) if template else normalize_permissions({})
    return cleaned


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
        permissions=_permissions_for(role, payload.permissions),
    )
    db.add(user)
    db.flush()
    _audit_user(db, current_user, user, "user_create", {"role": role.name, "permissions": user.permissions})
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
    old = {"role": user.role.name, "permissions": user.permissions, "is_active": user.is_active}
    role = user.role
    if "role_id" in data:
        role = db.query(Role).filter(Role.id == data["role_id"]).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rolle nicht gefunden")
    # Vor jeder Änderung prüfen: die letzte Leitung darf nicht wegfallen
    will_be_active = data.get("is_active", user.is_active) is not False
    _ensure_manager_remains(db, user, role.name in MANAGER_ROLES and will_be_active)
    if "role_id" in data:
        user.role_id = role.id
        user.role = role
        data.pop("role_id")
    if "permissions" in data or "role_id" in payload.model_fields_set:
        user.permissions = _permissions_for(role, data.pop("permissions", None) or (
            None if role.name in MANAGER_ROLES else user.permissions))
    for key, value in data.items():
        setattr(user, key, value)
    db.flush()
    db.refresh(user)
    _audit_user(db, current_user, user, "user_update", {
        "role": role.name, "permissions": user.permissions, "is_active": user.is_active}, old)
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
    _ensure_manager_remains(db, user, False)
    user.is_active = False
    db.flush()
    _audit_user(db, current_user, user, "user_deactivate", {"is_active": False}, {"is_active": True})
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
