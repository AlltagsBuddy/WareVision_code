"""Automatisches Änderungsprotokoll (Audit-Log) für Stammdaten und Einstellungen.

Für Bereiche ohne eigene Protokollierung (Lieferanten, Fahrzeuge, Artikel, Lager, Wartungspläne,
Einstellungen …) schreibt WareVision bei jedem Speichern einen Eintrag: wer (angemeldeter Benutzer),
wann, was (Anlegen/Ändern/Löschen) und welche Felder sich von welchem auf welchen Wert geändert haben.
Geheimnisse (API-Keys, Passwörter) werden nie im Klartext protokolliert.

Der angemeldete Benutzer wird in get_current_user an der Datenbank-Sitzung hinterlegt
(session.info["audit_user_id"]). Ohne angemeldeten Benutzer (Skripte, Hintergrundaufgaben)
wird nichts automatisch protokolliert.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

AUDIT_USER_KEY = "audit_user_id"
_SKIP_COLUMNS = {"id", "created_at", "updated_at"}
_SECRET_MARKERS = ("api_key", "password", "secret", "token")
_MAX_TEXT = 500


def _entity_types() -> dict[type, str]:
    from app.models import (
        AppSetting,
        Article,
        ArticleCategory,
        LaborRate,
        MaintenancePlan,
        MaintenanceTask,
        Manufacturer,
        StockMovement,
        StockReservation,
        StorageLocation,
        Supplier,
        Vehicle,
        VehicleModel,
    )

    return {
        AppSetting: "setting",
        Article: "article",
        ArticleCategory: "article_category",
        LaborRate: "labor_rate",
        MaintenancePlan: "maintenance_plan",
        MaintenanceTask: "maintenance_task",
        Manufacturer: "manufacturer",
        StockMovement: "stock_movement",
        StockReservation: "stock_reservation",
        StorageLocation: "storage_location",
        Supplier: "supplier",
        Vehicle: "vehicle",
        VehicleModel: "vehicle_model",
    }


def _plain(value):
    """Wert JSON-tauglich machen."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    text = str(value)
    return text if len(text) <= _MAX_TEXT else text[:_MAX_TEXT] + "…"


def _is_secret(name: str) -> bool:
    n = name.lower()
    return any(m in n for m in _SECRET_MARKERS)


def _setting_values(obj, value) -> dict:
    """Einstellung: Schlüssel und Wert (Geheimnisse nur als „gesetzt“/„entfernt“)."""
    key = getattr(obj, "key", "")
    if _is_secret(key):
        return {key: "(gesetzt)" if value else "(entfernt)"}
    return {key: _plain(value)}


def _columns(obj) -> list[str]:
    return [a.key for a in inspect(obj).mapper.column_attrs if a.key not in _SKIP_COLUMNS]


def _snapshot(obj) -> dict:
    out = {}
    for name in _columns(obj):
        v = getattr(obj, name, None)
        if v is None or v == "":
            continue
        out[name] = "(gesetzt)" if _is_secret(name) else _plain(v)
    return out


def _changes(obj) -> tuple[dict, dict]:
    old, new = {}, {}
    state = inspect(obj)
    for name in _columns(obj):
        hist = state.attrs[name].history
        if not hist.has_changes():
            continue
        before = hist.deleted[0] if hist.deleted else None
        after = hist.added[0] if hist.added else None
        if _plain(before) == _plain(after):
            continue
        if _is_secret(name):
            old[name], new[name] = "(gesetzt)" if before else "–", "(gesetzt)" if after else "(entfernt)"
        else:
            old[name], new[name] = _plain(before), _plain(after)
    return old, new


@event.listens_for(Session, "before_flush")
def _audit_before_flush(session: Session, flush_context, instances) -> None:
    user_id = session.info.get(AUDIT_USER_KEY)
    if not user_id:
        return
    types = _entity_types()
    entries: list[AuditLog] = []

    for obj in list(session.new):
        etype = types.get(type(obj))
        if not etype:
            continue
        if obj.id is None:
            obj.id = uuid.uuid4()  # ID vorab vergeben, damit der Eintrag darauf verweisen kann
        values = _setting_values(obj, obj.value) if etype == "setting" else _snapshot(obj)
        entries.append(AuditLog(user_id=user_id, entity_type=etype, entity_id=obj.id,
                                action="create", new_values=values))

    for obj in list(session.dirty):
        etype = types.get(type(obj))
        if not etype or not session.is_modified(obj, include_collections=False):
            continue
        old, new = _changes(obj)
        if not new and not old:
            continue
        if etype == "setting":
            key = getattr(obj, "key", "")
            old = _setting_values(obj, old.get("value")) if "value" in old else {}
            new = _setting_values(obj, new.get("value")) if "value" in new else {}
            if _is_secret(key):
                old = {}
        entries.append(AuditLog(user_id=user_id, entity_type=etype, entity_id=obj.id,
                                action="update", old_values=old or None, new_values=new or None))

    for obj in list(session.deleted):
        etype = types.get(type(obj))
        if not etype:
            continue
        old = _setting_values(obj, obj.value) if etype == "setting" else _snapshot(obj)
        entries.append(AuditLog(user_id=user_id, entity_type=etype, entity_id=obj.id,
                                action="delete", old_values=old))

    for e in entries:
        session.add(e)
