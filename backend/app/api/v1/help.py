"""Hilfe-API: Anleitung, Suche und KI-Assistent für funktionale Fragen."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.app_setting import AppSetting
from app.models.user import User
from app.services import help_assistant
from app.services.audit import log_audit

router = APIRouter(prefix="/help", tags=["help"])


class HelpTurn(BaseModel):
    """Bisherige Nachricht im Hilfe-Chat."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=6000)


class HelpQuestion(BaseModel):
    """Frage an die Hilfe."""

    question: str = Field(..., min_length=2, max_length=help_assistant.MAX_QUESTION_CHARS)
    history: list[HelpTurn] = Field(default_factory=list, max_length=20)


def _ai_settings(db: Session) -> tuple[str | None, str]:
    """API-Key und Modell für die KI-Hilfe aus den Einstellungen."""
    rows = db.query(AppSetting).filter(AppSetting.key.in_(("ai_help_api_key", "ai_help_model"))).all()
    values = {r.key: (r.value or "").strip() for r in rows}
    return values.get("ai_help_api_key") or None, values.get("ai_help_model") or help_assistant.DEFAULT_MODEL


@router.get("/status")
def help_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Ist die KI-Hilfe eingerichtet?"""
    api_key, model = _ai_settings(db)
    return {"ai_enabled": bool(api_key), "model": model if api_key else None}


@router.get("/articles")
def help_articles(current_user: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    """Komplette Anleitung (Kapitel mit Abschnitten)."""
    return [
        {
            "id": a.id,
            "title": a.title,
            "sections": [{"id": s.id, "heading": s.heading, "text": s.text} for s in a.sections],
        }
        for a in help_assistant.load_articles()
    ]


@router.get("/search")
def help_search(
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=2, max_length=200),
) -> list[dict]:
    """Stichwortsuche in der Anleitung."""
    return [
        {"id": s.id, "article_id": s.article_id, "article_title": s.article_title, "heading": s.heading, "text": s.text}
        for s in help_assistant.search(q, limit=8)
    ]


@router.post("/ask")
@limiter.limit("20/minute")
def help_ask(
    request: Request,
    payload: HelpQuestion,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Frage beantworten – mit KI, falls eingerichtet, sonst per Stichwortsuche."""
    api_key, model = _ai_settings(db)
    result = help_assistant.ask(
        payload.question,
        [t.model_dump() for t in payload.history],
        api_key,
        model,
    )
    if result["mode"] == "ai":
        # Nur die Nutzung protokollieren, nicht den Inhalt der Frage (Datensparsamkeit)
        log_audit(db, user_id=current_user.id, entity_type="help", action="ai_question")
        db.commit()
    return result
