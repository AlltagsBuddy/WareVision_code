"""Application configuration."""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "WareVision"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://warevision:warevision@localhost:5432/warevision"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS – Basis-Origins + optionale Zusatz-Origins (kommagetrennt) für externe Tests
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ORIGINS_EXTRA: str = ""  # z.B. "https://test.warevision.de,http://192.168.1.100:5173"

    # Uploads
    UPLOAD_DIR: str = "uploads"

    @computed_field
    @property
    def cors_origins_resolved(self) -> list[str]:
        """CORS-Origins inkl. CORS_ORIGINS_EXTRA (kommagetrennt)."""
        extra = [o.strip() for o in self.CORS_ORIGINS_EXTRA.split(",") if o.strip()]
        return [*self.CORS_ORIGINS, *extra]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
