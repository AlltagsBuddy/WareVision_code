"""Hintergrundaufgaben-API: Aufgaben auflisten und manuell auslösen."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_admin
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Verzeichnis aller verfügbaren Aufgaben
_TASKS: dict[str, dict] = {}


def _load_task_registry() -> dict[str, dict]:
    """Aufgaben-Registry lazy laden."""
    if _TASKS:
        return _TASKS
    from app.tasks.reminders import TASK_META as rm
    from app.tasks.maintenance_check import TASK_META as mc
    _TASKS[rm["name"]] = rm
    _TASKS[mc["name"]] = mc
    return _TASKS


@router.get("")
def list_tasks(
    current_user: Annotated[User, Depends(require_admin)],
) -> list[dict]:
    """Alle verfügbaren Hintergrundaufgaben auflisten."""
    return list(_load_task_registry().values())


@router.post("/{task_name}/run")
def run_task(
    task_name: str,
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Hintergrundaufgabe manuell auslösen. Gibt task_id zurück."""
    registry = _load_task_registry()
    if task_name not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aufgabe '{task_name}' nicht gefunden",
        )
    try:
        from app.worker import celery_app
        result = celery_app.send_task(task_name)
        return {"task_id": result.id, "task_name": task_name, "status": "queued"}
    except Exception as exc:
        logger.exception("Aufgabe konnte nicht gestartet werden: %s", task_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Aufgabe konnte nicht gestartet werden: {exc}",
        ) from exc


@router.get("/{task_id}/status")
def get_task_status(
    task_id: str,
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Status einer laufenden oder abgeschlossenen Aufgabe abfragen."""
    try:
        from celery.result import AsyncResult
        from app.worker import celery_app
        result = AsyncResult(task_id, app=celery_app)
        payload: dict = {"task_id": task_id, "status": result.status}
        if result.ready():
            if result.successful():
                payload["result"] = result.result
            else:
                payload["error"] = str(result.result)
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Status konnte nicht abgerufen werden: {exc}",
        ) from exc
