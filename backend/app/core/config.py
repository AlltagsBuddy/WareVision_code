"""Application configuration."""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRETS = {
    "change-me-in-production-use-long-random-string",
    "dev-secret-key-change-in-production",
    "",
}


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
    # "production" auf dem Server: strengere Prüfungen, keine API-Doku, 2FA Pflicht
    APP_ENV: str = "development"
    # Zwei-Faktor-Anmeldung für alle Benutzer verlangen (auf dem Server immer an)
    TWO_FACTOR_REQUIRED: bool = False
    # Öffentliche Selbstregistrierung (/register) erlauben
    REGISTRATION_ENABLED: bool = True
    # Öffentliche Adresse, z. B. https://quadparadies.warevision.de (für Links und CORS)
    PUBLIC_URL: str = ""

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

    # Monitoring
    SENTRY_DSN: str = ""  # leer = Sentry deaktiviert
    SENTRY_ENVIRONMENT: str = "production"

    @computed_field
    @property
    def cors_origins_resolved(self) -> list[str]:
        """CORS-Origins inkl. CORS_ORIGINS_EXTRA (kommagetrennt) und PUBLIC_URL."""
        extra = [o.strip() for o in self.CORS_ORIGINS_EXTRA.split(",") if o.strip()]
        if self.PUBLIC_URL:
            extra.append(self.PUBLIC_URL.rstrip("/"))
        base = [] if self.is_production else list(self.CORS_ORIGINS)
        return [*base, *extra]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"

    @property
    def two_factor_required(self) -> bool:
        return self.TWO_FACTOR_REQUIRED or self.is_production

    def production_problems(self) -> list[str]:
        """Einstellungen, mit denen der Server nicht starten darf."""
        problems = []
        if self.is_production:
            if self.SECRET_KEY in DEFAULT_SECRETS or len(self.SECRET_KEY) < 32:
                problems.append("SECRET_KEY ist nicht gesetzt oder zu kurz (mindestens 32 Zeichen).")
            if "warevision:warevision@" in self.DATABASE_URL:
                problems.append("Datenbank-Passwort ist das Standardpasswort.")
            if not self.PUBLIC_URL.startswith("https://"):
                problems.append("PUBLIC_URL muss mit https:// beginnen.")
        return problems


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
