"""Settings API - company info for invoices (admin only)."""

import os
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
    "invoice_vat_exemption_note",
    "ai_help_api_key",
    "ai_help_model",
    "company_logo_path",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "smtp_from",
    "smtp_tls",
    "termin_marktplatz_api_key",
    "termin_marktplatz_webhook_base_url",
    "termin_marktplatz_cancel_callback_url",
    "resend_api_key",
    "resend_from_email",
    "resend_from_name",
)

_UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")


def _settings_to_dict(db: Session) -> dict[str, str]:
    """Get settings as key-value dict."""
    rows = db.query(AppSetting).filter(AppSetting.key.in_(_SETTING_KEYS)).all()
    return {r.key: r.value or "" for r in rows}


@router.post("/logo", status_code=status.HTTP_200_OK)
async def upload_logo(
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
) -> dict:
    """Firmenlogo hochladen (PNG oder JPG, max 2 MB). Wird auf Rechnungen angezeigt."""
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PNG, JPG oder WebP erlaubt.",
        )
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datei zu gross. Maximal 2 MB.",
        )
    # Bild prüfen und als PNG speichern (WebP kann das PDF nicht einbetten; Transparenz bleibt erhalten)
    from io import BytesIO

    from PIL import Image as PILImage, ImageOps

    try:
        img = PILImage.open(BytesIO(content))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        # Für den Druck reicht ~1200 px Breite (60 mm bei über 500 dpi)
        img.thumbnail((1200, 1200))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bild konnte nicht gelesen werden.") from exc
    ext = ".png"
    logo_path = os.path.join(_UPLOAD_DIR, f"company_logo{ext}")
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    img.save(logo_path, format="PNG", optimize=True)

    # Altes Logo mit anderem Extension entfernen
    for old_ext in (".png", ".jpg", ".jpeg", ".webp"):
        if old_ext != ext:
            old_path = os.path.join(_UPLOAD_DIR, f"company_logo{old_ext}")
            if os.path.exists(old_path):
                os.remove(old_path)

    # Pfad in Einstellungen speichern
    row = db.query(AppSetting).filter(AppSetting.key == "company_logo_path").first()
    if row:
        row.value = logo_path
    else:
        db.add(AppSetting(key="company_logo_path", value=logo_path))
    db.commit()
    return {"logo_path": logo_path}


@router.get("/logo")
def get_logo(db: Annotated[Session, Depends(get_db)]):
    """Firmenlogo als Bild ausliefern (kein Auth erforderlich – fuer PDF-Vorschau)."""
    row = db.query(AppSetting).filter(AppSetting.key == "company_logo_path").first()
    if not row or not row.value or not os.path.isfile(row.value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Logo hinterlegt.")
    ext = os.path.splitext(row.value)[1].lower()
    media_type_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return FileResponse(row.value, media_type=media_type_map.get(ext, "image/png"))


@router.get("", response_model=AppSettingsOut)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    _=Depends(require_admin),
):
    """Get company settings (admin only)."""
    d = _settings_to_dict(db)
    smtp_pw = d.get("smtp_password", "")
    tm_api_key = d.get("termin_marktplatz_api_key", "")
    resend_key = d.get("resend_api_key", "")
    logo_path = d.get("company_logo_path", "")
    return AppSettingsOut(
        termin_marktplatz_configured=bool(tm_api_key and tm_api_key.strip()),
        termin_marktplatz_webhook_base_url=d.get("termin_marktplatz_webhook_base_url", ""),
        termin_marktplatz_cancel_callback_url=d.get("termin_marktplatz_cancel_callback_url", ""),
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
        invoice_vat_exemption_note=d.get("invoice_vat_exemption_note", ""),
        ai_help_api_key="********" if d.get("ai_help_api_key") else "",
        ai_help_model=d.get("ai_help_model", ""),
        ai_help_configured=bool(d.get("ai_help_api_key")),
        company_logo_path=logo_path,
        company_logo_set=bool(logo_path and os.path.isfile(logo_path)),
        smtp_host=d.get("smtp_host", ""),
        smtp_port=d.get("smtp_port", "587"),
        smtp_user=d.get("smtp_user", ""),
        smtp_password="********" if smtp_pw else "",
        smtp_from=d.get("smtp_from", ""),
        smtp_tls=d.get("smtp_tls", "true"),
        resend_api_key="********" if resend_key else "",
        resend_from_email=d.get("resend_from_email", ""),
        resend_from_name=d.get("resend_from_name", ""),
        resend_configured=bool(resend_key),
    )


def _get_api_key(db: Session) -> str | None:
    """Get termin_marktplatz_api_key (not exposed in GET)."""
    row = db.query(AppSetting).filter(AppSetting.key == "termin_marktplatz_api_key").first()
    return row.value if row and row.value else None


@router.post("/test-email")
def send_test_email(
    payload: dict = Body(default_factory=dict),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user=Depends(require_admin),
) -> dict:
    """Test-E-Mail versenden. recipient_email im Body optional (sonst company_email)."""
    from app.services.email import send_email

    d = _settings_to_dict(db)
    recipient = (payload or {}).get("recipient_email", "").strip()
    if not recipient:
        recipient = d.get("company_email", "").strip()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine Empfänger-Adresse. Bitte recipient_email angeben oder company_email hinterlegen.",
        )

    company_name = d.get("company_name", "WareVision").strip() or "WareVision"
    subject = f"WareVision Test-E-Mail – {company_name}"
    text_body = (
        f"Dies ist eine Test-E-Mail von {company_name}.\n\n"
        "Der E-Mail-Versand ist korrekt konfiguriert."
    )
    html_body = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px">
  <h2 style="color:#2c3e50">WareVision Test-E-Mail</h2>
  <p>Dies ist eine Test-E-Mail von <strong>{company_name}</strong>.</p>
  <p style="color:#27ae60;font-weight:bold">✓ Der E-Mail-Versand ist korrekt konfiguriert.</p>
</body>
</html>"""

    try:
        send_email(db, to_email=recipient, subject=subject, text_body=text_body, html_body=html_body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"E-Mail-Versand fehlgeschlagen: {exc}",
        ) from exc

    return {"message": f"Test-E-Mail erfolgreich an {recipient} gesendet.", "recipient": recipient}


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
    # Schlüsselfelder, die nie überschrieben werden wenn leer/Platzhalter
    _protected = {
        "smtp_password": {"", "********"},
        "termin_marktplatz_api_key": {""},
        "resend_api_key": {"", "********"},
        "ai_help_api_key": {"", "********"},
    }
    # KI-Hilfe-Key bewusst entfernen (leeres Feld bedeutet sonst „unverändert“)
    if payload.ai_help_api_key_remove:
        db.query(AppSetting).filter(AppSetting.key == "ai_help_api_key").delete()
    for key in _SETTING_KEYS:
        val = getattr(payload, key, None)
        if key in _protected and (val is None or val in _protected[key]):
            continue
        if val is not None:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            if row:
                row.value = val
            else:
                db.add(AppSetting(key=key, value=val))
    db.commit()
    d = _settings_to_dict(db)
    smtp_pw = d.get("smtp_password", "")
    tm_api_key = d.get("termin_marktplatz_api_key", "")
    resend_key = d.get("resend_api_key", "")
    logo_path = d.get("company_logo_path", "")
    return AppSettingsOut(
        termin_marktplatz_configured=bool(tm_api_key and tm_api_key.strip()),
        termin_marktplatz_webhook_base_url=d.get("termin_marktplatz_webhook_base_url", ""),
        termin_marktplatz_cancel_callback_url=d.get("termin_marktplatz_cancel_callback_url", ""),
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
        invoice_vat_exemption_note=d.get("invoice_vat_exemption_note", ""),
        ai_help_api_key="********" if d.get("ai_help_api_key") else "",
        ai_help_model=d.get("ai_help_model", ""),
        ai_help_configured=bool(d.get("ai_help_api_key")),
        company_logo_path=logo_path,
        company_logo_set=bool(logo_path and os.path.isfile(logo_path)),
        smtp_host=d.get("smtp_host", ""),
        smtp_port=d.get("smtp_port", "587"),
        smtp_user=d.get("smtp_user", ""),
        smtp_password="********" if smtp_pw else "",
        smtp_from=d.get("smtp_from", ""),
        smtp_tls=d.get("smtp_tls", "true"),
        resend_api_key="********" if resend_key else "",
        resend_from_email=d.get("resend_from_email", ""),
        resend_from_name=d.get("resend_from_name", ""),
        resend_configured=bool(resend_key),
    )
