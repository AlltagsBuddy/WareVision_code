"""Auth schemas."""

from pydantic import BaseModel, EmailStr, field_validator

# Mindestlänge für neue Passwörter (WareVision ist über das Internet erreichbar)
MIN_PASSWORD_LENGTH = 10


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Antwort auf die Passwort-Anmeldung.

    Ohne Zwei-Faktor kommt direkt access_token. Sonst kommt ein kurzlebiges challenge_token,
    mit dem der Code bestätigt (two_factor_required) oder 2FA eingerichtet wird (two_factor_setup_required).
    """

    access_token: str | None = None
    token_type: str = "bearer"
    two_factor_required: bool = False
    two_factor_setup_required: bool = False
    challenge_token: str | None = None


class TwoFactorVerifyRequest(BaseModel):
    challenge_token: str
    code: str | None = None
    recovery_code: str | None = None


class TwoFactorSetupRequest(BaseModel):
    challenge_token: str


class TwoFactorSetupStart(BaseModel):
    secret: str
    otpauth_uri: str
    qr_data_uri: str
    account: str


class TwoFactorConfirmRequest(BaseModel):
    challenge_token: str
    code: str


class TwoFactorConfirmResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    recovery_codes: list[str]


class TwoFactorCodeRequest(BaseModel):
    code: str


class TwoFactorStatus(BaseModel):
    enabled: bool
    required: bool
    enabled_at: str | None = None
    recovery_codes_left: int = 0


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
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben")
        return v


class RegisterResponse(BaseModel):
    """Antwort nach erfolgreicher Registrierung."""

    message: str


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
    role_label: str = ""
    is_manager: bool = False
    is_active: bool
    permissions: dict | None = None

    class Config:
        from_attributes = True
