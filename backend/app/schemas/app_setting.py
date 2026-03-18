"""App setting schemas."""

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    """Company settings for invoices and documents."""

    termin_marktplatz_configured: bool = False  # True wenn API-Key gesetzt (ohne Wert zu exponieren)
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
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_user: str = ""
    smtp_password: str = ""  # GET: "" oder "********" wenn gesetzt; nie echtes Passwort
    smtp_from: str = ""
    smtp_tls: str = "true"


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
    smtp_host: str | None = None
    smtp_port: str | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_tls: str | None = None
    termin_marktplatz_api_key: str | None = None
