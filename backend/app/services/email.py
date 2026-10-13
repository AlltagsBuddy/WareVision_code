"""E-Mail-Versand via Resend REST API oder SMTP-Fallback."""

import base64
import json
import logging
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

logger = logging.getLogger(__name__)

RESEND_SEND_URL = "https://api.resend.com/emails"
# Resend blockt Anfragen ohne User-Agent (HTTP 403, error code 1010)
_RESEND_USER_AGENT = "WareVision/1.0 (+https://warevision.de)"
# Anzahl Versuche bei transienten Netzwerkfehlern
_MAX_RETRIES = 2
# Wartezeit in Sekunden zwischen Versuchen
_RETRY_DELAY = 3


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_settings(db: Session, *keys: str) -> dict[str, str]:
    """Beliebige AppSettings als Dict laden."""
    rows = db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    return {r.key: (r.value or "").strip() for r in rows}


def _get_resend_settings(db: Session) -> dict[str, str]:
    """Resend-Einstellungen aus app_settings laden."""
    return _get_settings(
        db,
        "resend_api_key",
        "resend_from_email",
        "resend_from_name",
    )


def _get_smtp_settings(db: Session) -> dict[str, str]:
    """SMTP-Einstellungen aus app_settings laden."""
    return _get_settings(
        db,
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "smtp_from",
        "smtp_tls",
    )


# ---------------------------------------------------------------------------
# Resend REST API
# ---------------------------------------------------------------------------

def _send_via_resend(
    *,
    api_key: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachments: list[dict] | None = None,
) -> None:
    """
    Sendet eine E-Mail über die Resend REST API.
    attachments: Liste von {"filename": str, "content": str (base64)}
    Wirft ValueError bei Konfigurationsfehlern, RuntimeError bei API-Fehlern.
    Versucht bei transienten Fehlern bis zu _MAX_RETRIES Mal.
    """
    if not api_key:
        raise ValueError("Resend API-Key muss konfiguriert sein.")
    if not from_email:
        raise ValueError("Resend Absender-Adresse (resend_from_email) fehlt.")

    from_field = f"{from_name} <{from_email}>" if from_name else from_email

    payload: dict = {
        "from": from_field,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body
    if attachments:
        payload["attachments"] = attachments

    body = json.dumps(payload).encode("utf-8")

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        req = Request(
            RESEND_SEND_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": _RESEND_USER_AGENT,
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=15) as resp:
                if resp.status not in (200, 201):
                    raise RuntimeError(f"Resend antwortete mit Status {resp.status}")
            logger.info("Resend: E-Mail gesendet an %s – %s", to_email, subject)
            return
        except HTTPError as e:
            # HTTP-Fehler sind keine transienten Fehler – nicht wiederholen
            detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.error("Resend HTTP-Fehler %s an %s: %s", e.code, to_email, detail)
            raise RuntimeError(f"Resend HTTP-Fehler {e.code}: {detail}") from e
        except (URLError, OSError, TimeoutError) as e:
            last_exc = e
            logger.warning(
                "Resend Verbindungsfehler (Versuch %d/%d) an %s: %s",
                attempt, _MAX_RETRIES, to_email, e,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    logger.error("Resend: alle %d Versuche fehlgeschlagen für %s", _MAX_RETRIES, to_email)
    raise RuntimeError(f"Resend Verbindungsfehler nach {_MAX_RETRIES} Versuchen: {last_exc}") from last_exc


# ---------------------------------------------------------------------------
# Öffentliche API: einfache E-Mail (kein Anhang)
# ---------------------------------------------------------------------------

def send_email(
    db: Session,
    *,
    to_email: str,
    to_name: str = "",
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """
    Sendet eine einfache E-Mail ohne Anhang.
    Nutzt Resend wenn konfiguriert, sonst SMTP.
    Wirft ValueError / RuntimeError bei Fehlern.
    """
    rs = _get_resend_settings(db)
    if rs.get("resend_api_key"):
        _send_via_resend(
            api_key=rs["resend_api_key"],
            from_email=rs.get("resend_from_email", ""),
            from_name=rs.get("resend_from_name", ""),
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    else:
        _send_via_smtp(
            db=db,
            to_email=to_email,
            subject=subject,
            body=text_body,
            html_body=html_body,
        )


# ---------------------------------------------------------------------------
# Termin-E-Mails (nur für interne Termine, nicht für Terminmarktplatz)
# ---------------------------------------------------------------------------

def send_appointment_confirmation(
    db: Session,
    *,
    to_email: str,
    customer_name: str,
    title: str,
    starts_at: str,
    ends_at: str,
    company_name: str = "Quad Paradies Schoner",
) -> None:
    """
    Terminbestätigung an den Kunden senden (nur für interne Termine).
    starts_at / ends_at als formatierter String (z. B. 'Mo, 20.03.2025, 10:00 Uhr').
    """
    subject = f"Terminbestätigung – {title}"

    text_body = (
        f"Guten Tag {customer_name},\n\n"
        f"Ihr Termin wurde erfolgreich gebucht.\n\n"
        f"Termindetails:\n"
        f"  Betreff: {title}\n"
        f"  Beginn:  {starts_at}\n"
        f"  Ende:    {ends_at}\n\n"
        f"Falls Sie Fragen haben oder den Termin verschieben möchten, "
        f"kontaktieren Sie uns bitte.\n\n"
        f"Mit freundlichen Grüßen\n{company_name}"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px">
  <h2 style="color:#1a7f4b">Terminbestätigung</h2>
  <p>Guten Tag <strong>{customer_name}</strong>,</p>
  <p>Ihr Termin wurde erfolgreich gebucht.</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr>
      <td style="padding:8px 12px;background:#f5f5f5;font-weight:bold;width:120px">Betreff</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">{title}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;background:#f5f5f5;font-weight:bold">Beginn</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">{starts_at}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;background:#f5f5f5;font-weight:bold">Ende</td>
      <td style="padding:8px 12px">{ends_at}</td>
    </tr>
  </table>
  <p>Falls Sie Fragen haben oder den Termin verschieben möchten, kontaktieren Sie uns bitte.</p>
  <p>Mit freundlichen Grüßen<br><strong>{company_name}</strong></p>
</body>
</html>"""

    send_email(
        db,
        to_email=to_email,
        to_name=customer_name,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    logger.info("Terminbestätigung gesendet an %s für '%s'", to_email, title)


def send_appointment_cancellation(
    db: Session,
    *,
    to_email: str,
    customer_name: str,
    title: str,
    starts_at: str,
    reason: str | None = None,
    company_name: str = "Quad Paradies Schoner",
) -> None:
    """
    Stornierungsmail an den Kunden senden (nur für interne Termine).
    Für Terminmarktplatz-Termine läuft die Stornierung über den TM-Callback.
    starts_at als formatierter String.
    """
    subject = f"Terminabsage – {title}"
    reason_text = f"\n\nGrund: {reason}" if reason else ""

    text_body = (
        f"Guten Tag {customer_name},\n\n"
        f"leider müssen wir Ihren Termin absagen.{reason_text}\n\n"
        f"Stornierter Termin:\n"
        f"  Betreff: {title}\n"
        f"  Datum:   {starts_at}\n\n"
        f"Bitte kontaktieren Sie uns für einen neuen Termin.\n\n"
        f"Mit freundlichen Grüßen\n{company_name}"
    )

    reason_html = f"<p><strong>Grund:</strong> {reason}</p>" if reason else ""
    html_body = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px">
  <h2 style="color:#c0392b">Terminabsage</h2>
  <p>Guten Tag <strong>{customer_name}</strong>,</p>
  <p>leider müssen wir Ihren Termin absagen.</p>
  {reason_html}
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr>
      <td style="padding:8px 12px;background:#f5f5f5;font-weight:bold;width:120px">Betreff</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">{title}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;background:#f5f5f5;font-weight:bold">Datum</td>
      <td style="padding:8px 12px">{starts_at}</td>
    </tr>
  </table>
  <p>Bitte kontaktieren Sie uns für einen neuen Termin.</p>
  <p>Mit freundlichen Grüßen<br><strong>{company_name}</strong></p>
</body>
</html>"""

    send_email(
        db,
        to_email=to_email,
        to_name=customer_name,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    logger.info("Stornierungsmail gesendet an %s für '%s'", to_email, title)


# ---------------------------------------------------------------------------
# SMTP-Implementierungen
# ---------------------------------------------------------------------------

def _send_via_smtp(
    db: Session,
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    """Text-Mail (optional mit HTML-Alternativ) via SMTP."""
    settings = _get_smtp_settings(db)
    host = settings.get("smtp_host", "")
    if not host:
        raise ValueError(
            "Weder Resend noch SMTP ist konfiguriert. Bitte in Einstellungen eintragen."
        )

    port = int(settings.get("smtp_port", "587") or "587")
    use_tls = (settings.get("smtp_tls", "true").lower() or "true") == "true"
    user = settings.get("smtp_user", "")
    password = settings.get("smtp_password", "")
    from_addr = settings.get("smtp_from", "") or user

    if html_body:
        msg: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email

    if use_tls:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())

    logger.info("SMTP: E-Mail gesendet an %s: %s", to_email, subject)


def send_email_with_attachment(
    db: Session,
    *,
    to_email: str,
    subject: str,
    body: str,
    attachment_filename: str,
    attachment_data: bytes,
    attachment_content_type: str = "application/pdf",
) -> None:
    """
    E-Mail mit Anhang versenden (für Rechnungen und Dokumente).
    Nutzt Resend wenn konfiguriert, sonst SMTP-Fallback.
    """
    rs = _get_resend_settings(db)
    if rs.get("resend_api_key"):
        # Anhang als Base64 für Resend API
        attachment_b64 = base64.b64encode(attachment_data).decode("ascii")
        try:
            _send_via_resend(
                api_key=rs["resend_api_key"],
                from_email=rs.get("resend_from_email", ""),
                from_name=rs.get("resend_from_name", ""),
                to_email=to_email,
                subject=subject,
                text_body=body,
                attachments=[{"filename": attachment_filename, "content": attachment_b64}],
            )
        except Exception:
            logger.exception("E-Mail mit Anhang (Resend) fehlgeschlagen an %s: %s", to_email, subject)
            raise
        return

    # SMTP-Fallback
    settings = _get_smtp_settings(db)
    host = settings.get("smtp_host", "").strip()
    if not host:
        raise ValueError(
            "Weder Resend noch SMTP ist konfiguriert. Bitte in Einstellungen eintragen."
        )

    port = int(settings.get("smtp_port", "587").strip() or "587")
    use_tls = (settings.get("smtp_tls", "true").lower() or "true") == "true"
    user = settings.get("smtp_user", "").strip()
    password = settings.get("smtp_password", "").strip()
    from_addr = settings.get("smtp_from", "").strip() or user

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    main_type = (attachment_content_type or "application/pdf").split("/")[0]
    sub_type = (attachment_content_type or "application/pdf").split("/")[-1]
    if main_type == "image":
        part = MIMEImage(attachment_data, _subtype=sub_type)
    else:
        part = MIMEApplication(attachment_data, _subtype=sub_type or "pdf")
    part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
    msg.attach(part)

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            if use_tls:
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    if user and password:
                        server.login(user, password)
                    server.sendmail(from_addr, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(host, port) as server:
                    if user and password:
                        server.login(user, password)
                    server.sendmail(from_addr, [to_email], msg.as_string())
            logger.info("SMTP: E-Mail mit Anhang gesendet an %s: %s", to_email, subject)
            return
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            last_exc = e
            logger.warning(
                "SMTP Fehler mit Anhang (Versuch %d/%d) an %s: %s",
                attempt, _MAX_RETRIES, to_email, e,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    logger.error("SMTP: alle %d Versuche fehlgeschlagen für %s", _MAX_RETRIES, to_email)
    raise RuntimeError(f"E-Mail-Versand fehlgeschlagen nach {_MAX_RETRIES} Versuchen: {last_exc}") from last_exc
