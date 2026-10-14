"""App setting schemas."""

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    """Company settings for invoices and documents."""

    termin_marktplatz_configured: bool = False  # True wenn API-Key gesetzt (ohne Wert zu exponieren)
    termin_marktplatz_webhook_base_url: str = ""  # Optional: Basis-URL für Webhook (z.B. ngrok-URL)
    termin_marktplatz_cancel_callback_url: str = ""  # URL für Storno-Benachrichtigung (WareVision → Terminmarktplatz)
    company_name: str = ""
    company_address: str = ""
    company_vat_id: str = ""
    company_email: str = ""
    company_phone: str = ""
    company_website: str = ""
    company_bank_name: str = ""
    company_bank_iban: str = ""
    company_bank_bic: str = ""
    company_bank_account_holder: str = ""
    invoice_vat_exemption_note: str = ""  # Hinweistext für 0-%-Positionen (§ 14 Abs. 4 Nr. 8 UStG)
    company_logo_path: str = ""       # Dateipfad des Logos im Container
    company_logo_set: bool = False    # True wenn Logo-Datei vorhanden
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_user: str = ""
    smtp_password: str = ""  # GET: "" oder "********" wenn gesetzt; nie echtes Passwort
    smtp_from: str = ""
    smtp_tls: str = "true"
    # Resend
    resend_api_key: str = ""       # GET: "" oder "********" wenn gesetzt
    resend_from_email: str = ""
    resend_from_name: str = ""
    resend_configured: bool = False  # True wenn API-Key gesetzt
    # KI-Hilfe (Anthropic)
    ai_help_api_key: str = ""       # GET: "" oder "********" wenn gesetzt
    ai_help_model: str = ""
    ai_help_configured: bool = False


class AppSettingsUpdate(BaseModel):
    """Update company settings."""

    company_name: str | None = None
    company_address: str | None = None
    company_vat_id: str | None = None
    company_email: str | None = None
    company_phone: str | None = None
    company_website: str | None = None
    company_bank_name: str | None = None
    company_bank_iban: str | None = None
    company_bank_bic: str | None = None
    company_bank_account_holder: str | None = None
    invoice_vat_exemption_note: str | None = None
    smtp_host: str | None = None
    smtp_port: str | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_tls: str | None = None
    termin_marktplatz_api_key: str | None = None
    termin_marktplatz_webhook_base_url: str | None = None
    termin_marktplatz_cancel_callback_url: str | None = None
    # Resend
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    resend_from_name: str | None = None
    ai_help_api_key: str | None = None
    ai_help_model: str | None = None
    ai_help_api_key_remove: bool = False
