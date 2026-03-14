"""Auth API."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Login and get JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige E-Mail oder Passwort",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer ist deaktiviert",
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role_name=current_user.role.name,
        is_active=current_user.is_active,
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
