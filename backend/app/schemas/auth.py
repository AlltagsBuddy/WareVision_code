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


class RegisterRequest(BaseModel):
    """Registrierung neuer Benutzer."""

    email: str
    first_name: str
    last_name: str
    password: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Ungültiges E-Mail-Format")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Passwort muss mindestens 6 Zeichen haben")
        return v


class ChangePasswordRequest(BaseModel):
    """Change own password."""

    current_password: str
    new_password: str


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
