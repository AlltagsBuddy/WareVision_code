"""Auth schemas."""

from pydantic import BaseModel, EmailStr, field_validator


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    user_id: str | None = None


class LoginRequest(BaseModel):
    """Login request. Verwendet str für E-Mail, damit .local-Domains (z.B. admin@warevision.local) akzeptiert werden."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        """Einfache E-Mail-Formatprüfung (inkl. .local)."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Ungültiges E-Mail-Format")
        return v.strip().lower()


class UserResponse(BaseModel):
    """Current user response."""

    id: str
    email: str
    first_name: str
    last_name: str
    role_name: str
    is_active: bool

    class Config:
        from_attributes = True
