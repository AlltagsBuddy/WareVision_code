"""Auth schemas."""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    user_id: str | None = None


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


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
