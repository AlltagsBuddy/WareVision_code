"""Settings API - company info for invoices (admin only)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.schemas.app_setting import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTING_KEYS = (
    "company_name",
    "company_address",
    "company_vat_id",
    "company_email",
    "company_phone",
    "company_website",
    "company_bank_name",
    "company_bank_iban",
    "company_bank_bic",
    "company_bank_account_holder",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "smtp_from",
    "smtp_tls",
    "termin_marktplatz_api_key",
)


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
    smtp_pw = d.get("smtp_password", "")
    api_key = d.get("termin_marktplatz_api_key", "")
    return AppSettingsOut(
        termin_marktplatz_configured=bool(api_key and api_key.strip()),
        company_name=d.get("company_name", ""),
        company_address=d.get("company_address", ""),
        company_vat_id=d.get("company_vat_id", ""),
        company_email=d.get("company_email", ""),
        company_phone=d.get("company_phone", ""),
        company_website=d.get("company_website", ""),
        company_bank_name=d.get("company_bank_name", ""),
        company_bank_iban=d.get("company_bank_iban", ""),
        company_bank_bic=d.get("company_bank_bic", ""),
        company_bank_account_holder=d.get("company_bank_account_holder", ""),
        smtp_host=d.get("smtp_host", ""),
        smtp_port=d.get("smtp_port", "587"),
        smtp_user=d.get("smtp_user", ""),
        smtp_password="********" if smtp_pw else "",
        smtp_from=d.get("smtp_from", ""),
        smtp_tls=d.get("smtp_tls", "true"),
    )


def _get_api_key(db: Session) -> str | None:
    """Get termin_marktplatz_api_key (not exposed in GET)."""
    row = db.query(AppSetting).filter(AppSetting.key == "termin_marktplatz_api_key").first()
    return row.value if row and row.value else None


@router.get("/termin-marktplatz-api-key")
def get_termin_marktplatz_api_key(
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
) -> dict:
    """API-Schlüssel anzeigen (Admin only)."""
    key = _get_api_key(db)
    return {"api_key": key if key else None}


@router.patch("", response_model=AppSettingsOut)
def update_settings(
    payload: AppSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
):
    """Update company settings (admin only)."""
    for key in _SETTING_KEYS:
        val = getattr(payload, key, None)
        if key == "smtp_password" and (val is None or val == "********"):
            continue  # Passwort nicht überschreiben wenn leer oder Platzhalter
        if key == "termin_marktplatz_api_key" and (val is None or val == ""):
            continue  # API-Schlüssel nicht löschen wenn leer gelassen
        if val is not None:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            if row:
                row.value = val
            else:
                db.add(AppSetting(key=key, value=val))
    db.commit()
    d = _settings_to_dict(db)
    smtp_pw = d.get("smtp_password", "")
    api_key = d.get("termin_marktplatz_api_key", "")
    return AppSettingsOut(
        termin_marktplatz_configured=bool(api_key and api_key.strip()),
        company_name=d.get("company_name", ""),
        company_address=d.get("company_address", ""),
        company_vat_id=d.get("company_vat_id", ""),
        company_email=d.get("company_email", ""),
        company_phone=d.get("company_phone", ""),
        company_website=d.get("company_website", ""),
        company_bank_name=d.get("company_bank_name", ""),
        company_bank_iban=d.get("company_bank_iban", ""),
        company_bank_bic=d.get("company_bank_bic", ""),
        company_bank_account_holder=d.get("company_bank_account_holder", ""),
        smtp_host=d.get("smtp_host", ""),
        smtp_port=d.get("smtp_port", "587"),
        smtp_user=d.get("smtp_user", ""),
        smtp_password="********" if smtp_pw else "",
        smtp_from=d.get("smtp_from", ""),
        smtp_tls=d.get("smtp_tls", "true"),
    )
