"""WareVision - Warenwirtschafts- und Werkstattsystem."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB models."""
    init_db()
    yield
    # Shutdown if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

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
    """Health check for monitoring."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "WareVision API", "docs": "/docs"}
