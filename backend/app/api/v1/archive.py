"""Belegarchiv (GoBD): Übersicht, fehlende Originale nachziehen, Prüfsummen kontrollieren."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_right
from app.core.database import get_db
from app.models.user import User
from app.services import archive
from app.services.audit import log_audit

router = APIRouter(prefix="/archive", tags=["archive"])


@router.get("/status")
def archive_status(db: Annotated[Session, Depends(get_db)], _=Depends(require_right("accounting"))) -> dict:
    """Anzahl archivierter Originale und ausgegebener Belege ohne Original."""
    return archive.status(db)


@router.post("/backfill")
def archive_backfill(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("accounting"))],
) -> dict:
    """Fehlende Originale für bereits ausgegebene Belege einmalig erzeugen (gekennzeichnet als „nachträglich“)."""
    result = archive.backfill(db, current_user.id)
    log_audit(db, user_id=current_user.id, entity_type="archive", action="backfill", new_values=result["created"])
    db.commit()
    return {**result, "status": archive.status(db)}


@router.get("/verify")
def archive_verify(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("accounting"))],
) -> dict:
    """Alle Archivdateien auf Vorhandensein und unveränderten Inhalt (SHA-256) prüfen."""
    result = archive.verify_all(db)
    log_audit(db, user_id=current_user.id, entity_type="archive", action="verify",
              new_values={"checked": result["checked"], "problems": len(result["problems"])})
    db.commit()
    return result
