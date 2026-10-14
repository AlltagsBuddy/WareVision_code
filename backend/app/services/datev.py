"""DATEV-Export (Buchungsstapel und Personenkonten im DATEV-Format „EXTF“, Version 700).

Grundlage: DATEV-Formatbeschreibung „ASCII-Import: Feldbeschreibungen für Standardformate“
(Dok.-Nr. 1003221) – Buchungsstapel Formatversion 13 (125 Felder), Debitoren/Kreditoren
Formatversion 5 (254 Felder). Datei: Windows-1252 (ANSI), Semikolon, Dezimalkomma,
Texte in Anführungszeichen, Zeilenende CR/LF, Kopfzeile + Überschriftenzeile + Daten.

Buchungslogik (Automatikkonten, ohne BU-Schlüssel):
- Ausgangsrechnung: je Steuersatz eine Zeile, Umsatz = Brutto, Konto = Debitor (Soll),
  Gegenkonto = Erlöskonto. Storno-/Korrekturbelege mit Haben-Kennzeichen.
- Eingangsrechnung: Umsatz = Brutto, Konto = Kreditor (Haben), Gegenkonto = Aufwandskonto.
  Gutschriften des Lieferanten mit Soll-Kennzeichen.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.customer import Customer
from app.models.datev import DatevAccount
from app.models.incoming_invoice import IncomingInvoice
from app.models.invoice import Invoice
from app.services.datev_columns import BUCHUNGSSTAPEL_COLUMNS, PERSONENKONTEN_COLUMNS
from app.services.pdf import _vat_breakdown

_CENT = Decimal("0.01")

# Kontenvorschläge (Automatikkonten mit Umsatzsteuer/Vorsteuer bzw. ohne Steuer).
# Bitte mit dem Steuerberater abstimmen – sie können in den DATEV-Einstellungen geändert werden.
DEFAULT_ACCOUNTS = {
    "SKR03": {
        "revenue_19": "8400",   # Erlöse 19 % USt
        "revenue_7": "8300",    # Erlöse 7 % USt
        "revenue_0": "1590",    # Durchlaufende Posten (z. B. weiterberechnete Gebühren)
        "expense_19": "3400",   # Wareneingang 19 % Vorsteuer
        "expense_7": "3300",    # Wareneingang 7 % Vorsteuer
        "expense_0": "3200",    # Wareneingang (ohne Vorsteuer)
    },
    "SKR04": {
        "revenue_19": "4400",
        "revenue_7": "4300",
        "revenue_0": "1370",
        "expense_19": "5400",
        "expense_7": "5300",
        "expense_0": "5200",
    },
}
ACCOUNT_KEYS = tuple(DEFAULT_ACCOUNTS["SKR03"].keys())
RATE_KEY = {Decimal("19.00"): "19", Decimal("7.00"): "7", Decimal("0.00"): "0"}

SETTING_PREFIX = "datev_"
SETTING_FIELDS = (
    "consultant_number", "client_number", "chart", "account_length", "fiscal_year_start_month",
    "debtor_start", "creditor_start", "lock_bookings", *ACCOUNT_KEYS,
)

OUTGOING_STATUSES = ("issued", "partially_paid", "paid", "cancelled")
# Erlaubte Zeichen in Belegfeld 1 laut DATEV (Buchstaben, Ziffern und $ & % * + - /)
_BELEG_ALLOWED = re.compile(r"[^A-Za-z0-9$&%*+\-/]")


class DatevError(Exception):
    """Fachlicher Fehler beim DATEV-Export (Meldung für den Anwender)."""


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------

@dataclass
class DatevSettings:
    consultant_number: int | None = None
    client_number: int | None = None
    chart: str = "SKR03"
    account_length: int = 4
    fiscal_year_start_month: int = 1
    debtor_start: int | None = None
    creditor_start: int | None = None
    lock_bookings: bool = False
    accounts: dict[str, str] = field(default_factory=dict)

    @property
    def debtor_range(self) -> tuple[int, int]:
        """Debitoren: 1… bis 6… (bei Sachkontenlänge 4: 10000–69999)."""
        base = 10 ** self.account_length
        return base, 7 * base - 1

    @property
    def creditor_range(self) -> tuple[int, int]:
        """Kreditoren: 7… bis 9… (bei Sachkontenlänge 4: 70000–99999)."""
        base = 10 ** self.account_length
        return 7 * base, 10 * base - 1

    def account(self, kind: str, rate: Decimal) -> str | None:
        """Sachkonto für Erlös/Aufwand je Steuersatz (None = Steuersatz nicht unterstützt)."""
        key = RATE_KEY.get(Decimal(rate).quantize(_CENT))
        return self.accounts.get(f"{kind}_{key}") if key else None


def load_settings(db: Session) -> DatevSettings:
    """DATEV-Einstellungen lesen; leere Konten mit den Vorschlägen des Kontenrahmens füllen."""
    rows = db.query(AppSetting).filter(AppSetting.key.like(f"{SETTING_PREFIX}%")).all()
    raw = {r.key[len(SETTING_PREFIX):]: (r.value or "").strip() for r in rows}

    def as_int(name: str, default: int | None) -> int | None:
        try:
            return int(raw[name]) if raw.get(name) else default
        except ValueError:
            return default

    s = DatevSettings(
        consultant_number=as_int("consultant_number", None),
        client_number=as_int("client_number", None),
        chart=raw.get("chart") if raw.get("chart") in DEFAULT_ACCOUNTS else "SKR03",
        account_length=as_int("account_length", 4) or 4,
        fiscal_year_start_month=as_int("fiscal_year_start_month", 1) or 1,
        lock_bookings=raw.get("lock_bookings") == "true",
    )
    s.debtor_start = as_int("debtor_start", s.debtor_range[0])
    s.creditor_start = as_int("creditor_start", s.creditor_range[0])
    defaults = DEFAULT_ACCOUNTS[s.chart] if s.account_length == 4 else {}
    s.accounts = {k: raw.get(k) or defaults.get(k, "") for k in ACCOUNT_KEYS}
    return s


def save_settings(db: Session, values: dict) -> None:
    """Einstellungen speichern (nur bekannte Felder)."""
    for name in SETTING_FIELDS:
        if name not in values:
            continue
        val = values[name]
        if isinstance(val, bool):
            val = "true" if val else "false"
        val = "" if val is None else str(val).strip()
        key = SETTING_PREFIX + name
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = val
        else:
            db.add(AppSetting(key=key, value=val))


def settings_problems(s: DatevSettings) -> list[str]:
    """Was fehlt oder ist ungültig, bevor exportiert werden kann."""
    problems = []
    if not s.consultant_number or not (1001 <= s.consultant_number <= 9999999):
        problems.append("Beraternummer fehlt oder ist ungültig (1001 bis 9999999, vom Steuerberater).")
    if not s.client_number or not (1 <= s.client_number <= 99999):
        problems.append("Mandantennummer fehlt oder ist ungültig (1 bis 99999, vom Steuerberater).")
    if not (4 <= s.account_length <= 8):
        problems.append("Sachkontenlänge muss zwischen 4 und 8 liegen.")
    if not (1 <= s.fiscal_year_start_month <= 12):
        problems.append("Beginn des Wirtschaftsjahres muss ein Monat 1 bis 12 sein.")
    for key in ACCOUNT_KEYS:
        acc = s.accounts.get(key, "")
        if not acc.isdigit() or len(acc) != s.account_length:
            problems.append(f"Konto „{ACCOUNT_LABELS[key]}“ fehlt oder hat nicht {s.account_length} Stellen.")
    lo, hi = s.debtor_range
    if not s.debtor_start or not (lo <= s.debtor_start <= hi):
        problems.append(f"Erste Debitorennummer muss zwischen {lo} und {hi} liegen.")
    lo, hi = s.creditor_range
    if not s.creditor_start or not (lo <= s.creditor_start <= hi):
        problems.append(f"Erste Kreditorennummer muss zwischen {lo} und {hi} liegen.")
    return problems


ACCOUNT_LABELS = {
    "revenue_19": "Erlöse 19 %",
    "revenue_7": "Erlöse 7 %",
    "revenue_0": "Erlöse 0 % / durchlaufende Posten",
    "expense_19": "Wareneingang/Aufwand 19 %",
    "expense_7": "Wareneingang/Aufwand 7 %",
    "expense_0": "Wareneingang/Aufwand 0 %",
}


def fiscal_year_start(s: DatevSettings, day: date) -> date:
    """Beginn des Wirtschaftsjahres, in dem der Tag liegt."""
    start = date(day.year, s.fiscal_year_start_month, 1)
    return start if day >= start else date(day.year - 1, s.fiscal_year_start_month, 1)


# ---------------------------------------------------------------------------
# Personenkonten
# ---------------------------------------------------------------------------

def _customer_name(c: Customer) -> str:
    return (c.company_name or f"{c.first_name or ''} {c.last_name or ''}").strip() or "Kunde"


def _creditor_key(inc: IncomingInvoice) -> str:
    vat = re.sub(r"\s", "", (inc.supplier_vat_id or "")).upper()
    if vat:
        return f"vat:{vat}"
    return "name:" + re.sub(r"\s+", " ", inc.supplier_name.strip().lower())


class AccountAssigner:
    """Vergibt Personenkonten fortlaufend und merkt sie dauerhaft (nur beim echten Export)."""

    def __init__(self, db: Session, s: DatevSettings, persist: bool):
        self.db, self.s, self.persist = db, s, persist
        self.known = {(a.kind, a.ref_key): a for a in db.query(DatevAccount).all()}
        self.used_numbers = {a.account_number for a in self.known.values()}
        self.new: list[DatevAccount] = []

    def _next(self, kind: str) -> int:
        lo, hi = self.s.debtor_range if kind == "debtor" else self.s.creditor_range
        start = self.s.debtor_start if kind == "debtor" else self.s.creditor_start
        candidates = [n for n in self.used_numbers if lo <= n <= hi and n >= start]
        number = max(candidates) + 1 if candidates else start
        while number in self.used_numbers:
            number += 1
        if number > hi:
            raise DatevError(f"Keine freien {'Debitoren' if kind == 'debtor' else 'Kreditoren'}nummern mehr ({lo}–{hi}).")
        return number

    def get(self, kind: str, ref_key: str, name: str) -> DatevAccount:
        acc = self.known.get((kind, ref_key))
        if acc is None:
            acc = DatevAccount(kind=kind, ref_key=ref_key, name=name[:255], account_number=self._next(kind))
            self.known[(kind, ref_key)] = acc
            self.used_numbers.add(acc.account_number)
            self.new.append(acc)
            if self.persist:
                self.db.add(acc)
        return acc


# ---------------------------------------------------------------------------
# Buchungen
# ---------------------------------------------------------------------------

@dataclass
class Booking:
    amount: Decimal          # immer positiv
    debit_credit: str        # S oder H (bezogen auf „Konto“)
    account: int             # Personenkonto
    counter_account: str     # Sachkonto
    doc_date: date
    doc_number: str
    text: str
    service_date: date | None = None
    due_date: date | None = None


@dataclass
class ExportResult:
    outgoing: list[Booking] = field(default_factory=list)
    incoming: list[Booking] = field(default_factory=list)
    debtors: dict[int, Customer] = field(default_factory=dict)
    creditors: dict[int, IncomingInvoice] = field(default_factory=dict)
    hints: list[str] = field(default_factory=list)
    outgoing_docs: int = 0
    incoming_docs: int = 0
    new_accounts: int = 0


def _beleg(number: str) -> str:
    """Belegfeld 1: nur erlaubte Zeichen, höchstens 36 Stellen."""
    return _BELEG_ALLOWED.sub("-", number.strip())[:36]


def collect(db: Session, s: DatevSettings, date_from: date, date_to: date, persist: bool,
            include_incoming: bool = True) -> ExportResult:
    """Buchungen für den Zeitraum ermitteln. persist=True vergibt Personenkonten dauerhaft."""
    if date_from > date_to:
        raise DatevError("Das Startdatum muss vor dem Enddatum liegen.")
    fy = fiscal_year_start(s, date_from)
    fy_end = date(fy.year + 1, fy.month, 1)
    if date_to >= fy_end:
        last_day = date.fromordinal(fy_end.toordinal() - 1)
        raise DatevError(
            "Ein DATEV-Buchungsstapel darf nur ein Wirtschaftsjahr enthalten. "
            f"Bitte höchstens bis {last_day.strftime('%d.%m.%Y')} exportieren."
        )

    res = ExportResult()
    assigner = AccountAssigner(db, s, persist)

    invoices = (
        db.query(Invoice)
        .filter(Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to, Invoice.status.in_(OUTGOING_STATUSES))
        .order_by(Invoice.invoice_date, Invoice.invoice_number)
        .all()
    )
    for inv in invoices:
        breakdown = _vat_breakdown(inv.items)
        unsupported = [r for r, _, _ in breakdown if s.account("revenue", r) is None]
        if unsupported:
            res.hints.append(
                f"{inv.invoice_number}: Steuersatz {', '.join(f'{r.normalize():f} %' for r in unsupported)} "
                "wird nicht unterstützt – Beleg nicht exportiert, bitte manuell buchen."
            )
            continue
        customer = inv.customer
        acc = assigner.get("debtor", f"customer:{customer.id}", _customer_name(customer))
        res.debtors[acc.account_number] = customer
        doc_type = getattr(inv, "document_type", "invoice") or "invoice"
        ref = getattr(inv, "referenced_invoice", None)
        prefix = {"cancellation": "Storno", "correction": "Korrektur"}.get(doc_type, "")
        text = (f"{prefix} zu {ref.invoice_number} " if prefix and ref else "") + _customer_name(customer)
        res.outgoing_docs += 1
        for rate, basis, tax in breakdown:
            gross = (basis + tax).quantize(_CENT)
            if gross == 0:
                continue
            res.outgoing.append(Booking(
                amount=abs(gross),
                debit_credit="S" if gross > 0 else "H",
                account=acc.account_number,
                counter_account=s.account("revenue", rate),
                doc_date=inv.invoice_date,
                doc_number=_beleg(inv.invoice_number),
                text=text[:60],
                service_date=inv.service_date,
                due_date=inv.due_date if doc_type == "invoice" else None,
            ))

    if include_incoming:
        incoming = (
            db.query(IncomingInvoice)
            .filter(IncomingInvoice.invoice_date >= date_from, IncomingInvoice.invoice_date <= date_to)
            .order_by(IncomingInvoice.invoice_date, IncomingInvoice.invoice_number)
            .all()
        )
        for inc in incoming:
            label = f"{inc.supplier_name} {inc.invoice_number}"
            if inc.status == "cancelled":
                res.hints.append(f"Eingangsrechnung {label}: storniert – nicht exportiert.")
                continue
            rate = Decimal(inc.vat_rate).quantize(_CENT)
            counter = s.account("expense", rate)
            if counter is None:
                res.hints.append(f"Eingangsrechnung {label}: Steuersatz {rate.normalize():f} % wird nicht unterstützt – bitte manuell buchen.")
                continue
            net, vat, gross = Decimal(inc.net_amount), Decimal(inc.vat_amount), Decimal(inc.gross_amount)
            # Mehrere Steuersätze oder unstimmige Beträge können nicht sicher auf ein Konto gebucht werden
            if abs(net * rate / 100 - vat) > Decimal("0.02") or abs(net + vat - gross) > Decimal("0.01"):
                res.hints.append(
                    f"Eingangsrechnung {label}: Netto/MwSt/Brutto passen nicht zu {rate.normalize():f} % "
                    "(evtl. mehrere Steuersätze) – nicht exportiert, bitte manuell buchen."
                )
                continue
            if gross == 0:
                continue
            acc = assigner.get("creditor", _creditor_key(inc), inc.supplier_name)
            res.creditors[acc.account_number] = inc
            credit_note = bool(getattr(inc, "is_credit_note", False))
            positive = (gross > 0) != credit_note
            original_no = inc.invoice_number.strip()
            beleg = _beleg(original_no)
            text = ("Gutschrift " if credit_note else "") + inc.supplier_name
            if beleg != original_no:
                text = f"{text} Re-Nr. {original_no}"
            res.incoming_docs += 1
            res.incoming.append(Booking(
                amount=abs(gross),
                debit_credit="H" if positive else "S",
                account=acc.account_number,
                counter_account=counter,
                doc_date=inc.invoice_date,
                doc_number=beleg,
                text=text[:60],
                service_date=inc.service_date,
                due_date=inc.due_date if not credit_note else None,
            ))

    res.new_accounts = len(assigner.new)
    return res


# ---------------------------------------------------------------------------
# Dateien
# ---------------------------------------------------------------------------

def _q(text: str | None) -> str:
    """Textfeld in Anführungszeichen (innere Anführungszeichen verdoppelt)."""
    if text is None or text == "":
        return ""
    return '"' + str(text).replace('"', '""').replace("\r", " ").replace("\n", " ") + '"'


def _amount(value: Decimal) -> str:
    return f"{value.quantize(_CENT):f}".replace(".", ",")


def _header(s: DatevSettings, category: int, name: str, version: int, user: str,
            date_from: date | None, date_to: date | None, description: str, fy_start: date) -> str:
    """Kopfzeile (31 Felder) nach DATEV-Format, Version 700."""
    is_batch = category == 21
    fields = [
        _q("EXTF"), "700", str(category), _q(name), str(version),
        datetime.now().strftime("%Y%m%d%H%M%S") + "000",   # 6 erzeugt am
        "",                                                # 7 importiert
        _q("WV"),                                          # 8 Herkunft
        _q(user[:25]),                                     # 9 exportiert von
        "",                                                # 10 importiert von
        str(s.consultant_number), str(s.client_number),    # 11 Berater, 12 Mandant
        fy_start.strftime("%Y%m%d"),                       # 13 WJ-Beginn
        str(s.account_length),                             # 14 Sachkontenlänge
        date_from.strftime("%Y%m%d") if is_batch else "",  # 15 Datum vom
        date_to.strftime("%Y%m%d") if is_batch else "",    # 16 Datum bis
        _q(description[:30]) if is_batch else "",          # 17 Bezeichnung
        "",                                                # 18 Diktatkürzel
        "1" if is_batch else "",                           # 19 Buchungstyp (1 = Finanzbuchführung)
        "0" if is_batch else "",                           # 20 Rechnungslegungszweck
        ("1" if s.lock_bookings else "0") if is_batch else "",  # 21 Festschreibung
        _q("EUR") if is_batch else "",                     # 22 WKZ
        "", "", "", "",                                    # 23–26 reserviert/Derivatskennzeichen
        _q(s.chart[-2:]),                                  # 27 SKR
        "", "", "", "",                                    # 28–31
    ]
    assert len(fields) == 31
    return ";".join(fields)


def _encode(lines: list[str]) -> bytes:
    """Windows-1252, Zeilenende CR/LF. Nicht darstellbare Zeichen werden ersetzt."""
    return ("\r\n".join(lines) + "\r\n").encode("cp1252", errors="replace")


def buchungsstapel_csv(s: DatevSettings, bookings: list[Booking], date_from: date, date_to: date,
                       description: str, user: str) -> bytes:
    """Buchungsstapel (Formatkategorie 21, Formatversion 13)."""
    idx = {name: i for i, name in enumerate(BUCHUNGSSTAPEL_COLUMNS)}
    lines = [
        _header(s, 21, "Buchungsstapel", 13, user, date_from, date_to, description, fiscal_year_start(s, date_from)),
        ";".join(BUCHUNGSSTAPEL_COLUMNS),
    ]
    for b in bookings:
        row = [""] * len(BUCHUNGSSTAPEL_COLUMNS)
        row[idx["Umsatz (ohne Soll/Haben-Kz)"]] = _amount(b.amount)
        row[idx["Soll/Haben-Kennzeichen"]] = _q(b.debit_credit)
        row[idx["WKZ Umsatz"]] = _q("EUR")
        row[idx["Konto"]] = str(b.account)
        row[idx["Gegenkonto (ohne BU-Schlüssel)"]] = b.counter_account
        row[idx["Belegdatum"]] = b.doc_date.strftime("%d%m")
        row[idx["Belegfeld 1"]] = _q(b.doc_number)
        row[idx["Buchungstext"]] = _q(b.text)
        row[idx["Festschreibung"]] = "1" if s.lock_bookings else "0"
        if b.service_date:
            row[idx["Leistungsdatum"]] = b.service_date.strftime("%d%m%Y")
        if b.due_date:
            row[idx["Fälligkeit"]] = b.due_date.strftime("%d%m%Y")
        lines.append(";".join(row))
    return _encode(lines)


def _split_vat_id(vat_id: str | None) -> tuple[str, str]:
    v = re.sub(r"\s", "", vat_id or "").upper()
    if len(v) > 2 and v[:2].isalpha():
        return v[:2], v[2:]
    return "", ""


def _main_address(c: Customer):
    addresses = list(c.addresses or [])
    for wanted in ("billing", "main", None):
        for a in addresses:
            if wanted is None or a.address_type == wanted:
                return a
    return None


def _country_code(country: str | None) -> str:
    c = (country or "").strip().lower()
    if c in ("", "deutschland", "germany", "de"):
        return "DE"
    if c in ("österreich", "austria", "at"):
        return "AT"
    if c in ("schweiz", "switzerland", "ch"):
        return "CH"
    return c[:2].upper() if len(c) == 2 else ""


def personenkonten_csv(s: DatevSettings, debtors: dict[int, Customer], creditors: dict[int, IncomingInvoice],
                       user: str, fy_start: date) -> bytes:
    """Debitoren/Kreditoren-Stammdaten (Formatkategorie 16, Formatversion 5)."""
    idx = {name: i for i, name in enumerate(PERSONENKONTEN_COLUMNS)}
    lines = [
        _header(s, 16, "Debitoren/Kreditoren", 5, user, None, None, "", fy_start),
        ";".join(PERSONENKONTEN_COLUMNS),
    ]

    def new_row(number: int) -> list[str]:
        row = [""] * len(PERSONENKONTEN_COLUMNS)
        row[idx["Konto"]] = str(number)
        return row

    for number in sorted(debtors):
        c = debtors[number]
        row = new_row(number)
        if c.customer_type == "B2B" and c.company_name:
            row[idx["Name (Adressatentyp Unternehmen)"]] = _q(c.company_name[:50])
            row[idx["Adressatentyp"]] = "2"
        else:
            row[idx["Name (Adressatentyp natürl. Person)"]] = _q((c.last_name or c.company_name or "")[:30])
            row[idx["Vorname (Adressatentyp natürl. Person)"]] = _q((c.first_name or "")[:30])
            row[idx["Adressatentyp"]] = "1"
        row[idx["Kurzbezeichnung"]] = _q(_customer_name(c)[:15])
        land, ustid = _split_vat_id(c.vat_id)
        if land:
            row[idx["EU-Land"]] = _q(land)
            row[idx["EU-USt-IdNr."]] = _q(ustid)
        a = _main_address(c)
        if a is not None:
            row[idx["Straße"]] = _q(f"{a.street} {a.house_number or ''}".strip()[:36])
            row[idx["Postleitzahl"]] = _q((a.postal_code or "")[:10])
            row[idx["Ort"]] = _q((a.city or "")[:30])
            row[idx["Land"]] = _q(_country_code(a.country))
        if c.email:
            row[idx["E-Mail"]] = _q(c.email[:60])
        if c.phone:
            row[idx["Telefon"]] = _q(c.phone[:60])
        lines.append(";".join(row))

    for number in sorted(creditors):
        inc = creditors[number]
        row = new_row(number)
        row[idx["Name (Adressatentyp Unternehmen)"]] = _q(inc.supplier_name[:50])
        row[idx["Adressatentyp"]] = "2"
        row[idx["Kurzbezeichnung"]] = _q(inc.supplier_name[:15])
        land, ustid = _split_vat_id(inc.supplier_vat_id)
        if land:
            row[idx["EU-Land"]] = _q(land)
            row[idx["EU-USt-IdNr."]] = _q(ustid)
        lines.append(";".join(row))
    return _encode(lines)


def readme(s: DatevSettings, res: ExportResult, date_from: date, date_to: date) -> bytes:
    """Begleittext für den Steuerberater (UTF-8)."""
    acc = "\n".join(f"  {ACCOUNT_LABELS[k]}: {s.accounts[k]}" for k in ACCOUNT_KEYS)
    hints = "\n".join(f"  - {h}" for h in res.hints) or "  keine"
    text = f"""DATEV-Export aus WareVision
Zeitraum: {date_from.strftime('%d.%m.%Y')} bis {date_to.strftime('%d.%m.%Y')}
Berater-Nr.: {s.consultant_number}   Mandanten-Nr.: {s.client_number}
Kontenrahmen: {s.chart}, Sachkontenlänge {s.account_length}, WJ-Beginn {fiscal_year_start(s, date_from).strftime('%d.%m.%Y')}
Festschreibung: {'ja' if s.lock_bookings else 'nein'}

Dateien (DATEV-Format EXTF 700, Windows-1252):
  EXTF_Buchungsstapel_Ausgang_*.csv   Ausgangsrechnungen, Storno- und Korrekturbelege ({len(res.outgoing)} Buchungen aus {res.outgoing_docs} Belegen)
  EXTF_Buchungsstapel_Eingang_*.csv   Eingangsrechnungen ({len(res.incoming)} Buchungen)
  EXTF_Debitoren_Kreditoren.csv       Stammdaten der verwendeten Personenkonten

Buchungslogik:
  Je Rechnung und Steuersatz eine Buchung über den Bruttobetrag auf Automatikkonten (kein BU-Schlüssel).
  Ausgang: Konto = Debitor, Gegenkonto = Erlöskonto, Soll (Storno/Rechnungskorrektur: Haben).
  Eingang: Konto = Kreditor, Gegenkonto = Aufwandskonto, Haben (Gutschrift des Lieferanten: Soll).
  Belegfeld 1 = Belegnummer; bei Storno/Korrektur steht die Originalrechnung im Buchungstext.
  Zahlungen sind nicht enthalten (kommen über den Bankabruf).

Verwendete Sachkonten:
{acc}

Hinweise / nicht exportierte Belege:
{hints}

Die Belege selbst (PDF/ZUGFeRD) liefert der normale Steuerberater-Export (ZIP) aus WareVision.
"""
    return text.encode("utf-8")


def build_export_zip(s: DatevSettings, res: ExportResult, date_from: date, date_to: date, user: str) -> bytes:
    """ZIP mit Buchungsstapeln, Personenkonten und LIESMICH."""
    period = f"{date_from.strftime('%Y%m%d')}-{date_to.strftime('%Y%m%d')}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if res.outgoing:
            zf.writestr(f"EXTF_Buchungsstapel_Ausgang_{period}.csv",
                        buchungsstapel_csv(s, res.outgoing, date_from, date_to, "Ausgangsrechnungen", user))
        if res.incoming:
            zf.writestr(f"EXTF_Buchungsstapel_Eingang_{period}.csv",
                        buchungsstapel_csv(s, res.incoming, date_from, date_to, "Eingangsrechnungen", user))
        if res.debtors or res.creditors:
            zf.writestr("EXTF_Debitoren_Kreditoren.csv",
                        personenkonten_csv(s, res.debtors, res.creditors, user, fiscal_year_start(s, date_from)))
        zf.writestr("LIESMICH.txt", readme(s, res, date_from, date_to))
    return buf.getvalue()
