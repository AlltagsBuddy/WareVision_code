"""DATEV-Personenkonten: dauerhafte Zuordnung Kunde → Debitor bzw. Lieferant → Kreditor."""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DatevAccount(BaseModel):
    """Einmal vergebene Personenkontonummer (wird nie neu vergeben, damit DATEV-Konten stabil bleiben)."""

    __tablename__ = "datev_accounts"
    __table_args__ = (UniqueConstraint("kind", "ref_key", name="uq_datev_accounts_kind_ref"),)

    kind: Mapped[str] = mapped_column(String(10), nullable=False)          # debtor | creditor
    ref_key: Mapped[str] = mapped_column(String(300), nullable=False)      # customer:<id> | vat:<USt-IdNr> | name:<name>
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
