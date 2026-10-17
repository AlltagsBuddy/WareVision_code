"""WareVision - Warenwirtschafts- und Werkstattsystem."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.limiter import limiter
import app.services.auto_audit  # noqa: F401  (automatisches Änderungsprotokoll registrieren)

settings = get_settings()

# Auf dem Server nicht mit unsicheren Einstellungen starten
_problems = settings.production_problems()
if _problems:
    raise RuntimeError("WareVision startet nicht – unsichere Einstellungen: " + " ".join(_problems))

# Sentry initialisieren wenn DSN konfiguriert
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,  # 10 % der Requests als Performance-Trace
        send_default_pii=False,  # keine personenbezogenen Daten
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB models."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # API-Dokumentation nur lokal, nicht öffentlich auf dem Server
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_resolved,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    """Erweiterter Health-Check: prüft DB und Redis (für Checkly / Uptime-Monitoring)."""
    from datetime import datetime, timezone

    checks: dict[str, str] = {}
    overall = "ok"

    # Datenbankverbindung prüfen
    try:
        from sqlalchemy import text
        from app.core.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        overall = "degraded"

    # Redis-Verbindung prüfen (optional – kein Fehler wenn nicht konfiguriert)
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        overall = "degraded"

    if settings.is_production:
        # Öffentlich erreichbar: keine technischen Details preisgeben
        checks = {k: ("ok" if v == "ok" else "error") for k, v in checks.items()}
    return {
        "status": overall,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "WareVision API"} if settings.is_production else {"message": "WareVision API", "docs": "/docs"}
