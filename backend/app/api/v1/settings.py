"""Settings API - company info for invoices (admin only)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.schemas.app_setting import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTING_KEYS = ("company_name", "company_address", "company_vat_id")


def _settings_to_dict(db: Session) -> dict[str, str]:
    """Get settings as key-value dict."""
    rows = db.query(AppSetting).filter(AppSetting.key.in_(_SETTING_KEYS)).all()
    return {r.key: r.value or "" for r in rows}


@router.get("", response_model=AppSettingsOut)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
):
    """Get company settings (admin only)."""
    d = _settings_to_dict(db)
    return AppSettingsOut(
        company_name=d.get("company_name", ""),
        company_address=d.get("company_address", ""),
        company_vat_id=d.get("company_vat_id", ""),
    )


@router.patch("", response_model=AppSettingsOut)
def update_settings(
    payload: AppSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
):
    """Update company settings (admin only)."""
    for key in _SETTING_KEYS:
        val = getattr(payload, key, None)
        if val is not None:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            if row:
                row.value = val
            else:
                db.add(AppSetting(key=key, value=val))
    db.commit()
    d = _settings_to_dict(db)
    return AppSettingsOut(
        company_name=d.get("company_name", ""),
        company_address=d.get("company_address", ""),
        company_vat_id=d.get("company_vat_id", ""),
    )
