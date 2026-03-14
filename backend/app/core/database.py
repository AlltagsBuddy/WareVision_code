"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Import all models to register them with Base."""
    from app.models import (  # noqa: F401
        Role,
        User,
        Customer,
        CustomerAddress,
        Manufacturer,
        VehicleModel,
        Vehicle,
        Supplier,
        ArticleCategory,
        Article,
        StockMovement,
        StockReservation,
        Appointment,
        WorkshopOrder,
        WorkshopOrderItem,
        MaintenancePlan,
        MaintenanceTask,
        Invoice,
        InvoiceItem,
        Document,
        AuditLog,
        AppSetting,
    )


def get_db() -> Session:
    """Dependency for FastAPI - yields database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
