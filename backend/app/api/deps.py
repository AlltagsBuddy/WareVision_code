"""API dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.core.permissions import MODULES, RIGHTS, can_read, can_write, has_right, is_manager

security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> User:
    """Get current authenticated user from JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger oder abgelaufener Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer ist deaktiviert",
        )
    return user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Leitung: Admin oder Chef/Chefin (verwalten Benutzer, Rechte, Einstellungen)."""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur für Administrator oder Chef/Chefin",
        )
    return current_user


# Gleiche Bedeutung, sprechender Name
require_manager = require_admin


def require_right(right: str):
    """Sonderrecht verlangen (Admin und Chef haben alle Sonderrechte)."""

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_right(current_user, right):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Keine Berechtigung: {RIGHTS[right]}. Bitte Admin oder Chef/Chefin fragen.",
            )
        return current_user

    return dependency


# Öffentliche Schnittstellen ohne Benutzeranmeldung (eigene Absicherung, z. B. API-Schlüssel)
PUBLIC_PATH_MARKERS = ("/webhook/",)


def module_guard(module: str):
    """Bereichsrecht prüfen: Lesen (GET) braucht „sehen“, Ändern braucht „ändern“."""

    def dependency(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    ) -> None:
        if any(marker in request.url.path for marker in PUBLIC_PATH_MARKERS):
            return
        user = get_current_user(db, credentials)
        if is_manager(user):
            return
        label = MODULES.get(module, module)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            if not can_read(user, module):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail=f"Keine Berechtigung für den Bereich {label}")
        elif not can_write(user, module):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Im Bereich {label} nur Lesezugriff – Änderungen nicht erlaubt")

    return dependency
