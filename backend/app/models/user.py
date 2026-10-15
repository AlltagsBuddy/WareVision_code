"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.role import Role


class User(BaseModel):
    """System user."""

    __tablename__ = "users"

    role_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Modulberechtigungen
    # Zwei-Faktor-Anmeldung (TOTP); Geheimnis verschlüsselt, Wiederherstellungscodes nur als Hash
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_pending_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_last_counter: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_codes: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    role: Mapped["Role"] = relationship("Role", back_populates="users")
