"""E-Mail-Versand für Rechnungen und Dokumente."""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

logger = logging.getLogger(__name__)


def _get_smtp_settings(db: Session) -> dict[str, str]:
    """SMTP-Einstellungen aus app_settings laden."""
    keys = ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "smtp_tls")
    rows = db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    return {r.key: (r.value or "").strip() for r in rows}


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
    E-Mail mit Anhang versenden.
    Nutzt SMTP-Einstellungen aus app_settings.
    """
    settings = _get_smtp_settings(db)
    host = settings.get("smtp_host", "").strip()
    if not host:
        raise ValueError("SMTP ist nicht konfiguriert. Bitte in Einstellungen SMTP-Host eintragen.")

    port_str = settings.get("smtp_port", "587").strip() or "587"
    try:
        port = int(port_str)
    except ValueError:
        port = 587

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

    logger.info("E-Mail gesendet an %s: %s", to_email, subject)
