"""App setting schemas."""

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    """Company settings for invoices."""

    company_name: str = ""
    company_address: str = ""
    company_vat_id: str = ""


class AppSettingsUpdate(BaseModel):
    """Update company settings."""

    company_name: str | None = None
    company_address: str | None = None
    company_vat_id: str | None = None
