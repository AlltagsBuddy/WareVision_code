"""Rollen, Bereiche (Module) und Sonderrechte – eine Stelle für alle Berechtigungsregeln.

- Admin und Chef/Chefin ("Leitung") dürfen alles und verwalten Benutzer und Rechte.
- Büro, Werkstatt und Mitarbeiter dürfen, was ihnen je Bereich (sehen/ändern) und
  über Sonderrechte freigegeben ist. Die Rolle setzt beim Anlegen nur eine Vorlage.
- Der Server prüft das bei jeder Anfrage (nicht nur die Anzeige im Menü).
"""

from __future__ import annotations

from typing import Any

# Bereiche wie im Menü
MODULES: dict[str, str] = {
    "customers": "Kunden",
    "vehicles": "Fahrzeuge",
    "articles": "Artikel",
    "suppliers": "Lieferanten",
    "stock": "Lager",
    "stock_counts": "Inventur",
    "purchase_orders": "Bestellungen",
    "quotes": "Angebote",
    "workshop_orders": "Werkstattaufträge",
    "maintenance_plans": "Wartungspläne",
    "appointments": "Terminplaner",
    "invoices": "Rechnungen",
    "documents": "Dokumente",
}

# Sonderrechte, die Admin und Chef einzeln freigeben oder sperren
RIGHTS: dict[str, str] = {
    "invoices_manage": "Rechnungen anlegen, ausstellen, als bezahlt markieren, stornieren, korrigieren",
    "accounting": "Buchhaltung: Eingangsrechnungen, Steuerberater-/DATEV-Export, Belegarchiv",
    "dsgvo_export": "DSGVO: Auskunft/Datenexport eines Kunden",
    "dsgvo_delete": "DSGVO: Kunden löschen bzw. anonymisieren",
    "lager_einkauf": "Lager & Einkauf: Inventur starten/abschließen, Bestellungen versenden/stornieren, "
                     "Lagerorte/Kategorien verwalten, Stammdaten löschen",
}

MANAGER_ROLES = {"admin", "chef"}

ROLE_LABELS: dict[str, str] = {
    "admin": "Administrator",
    "chef": "Chef/Chefin",
    "buero": "Büro",
    "werkstatt": "Werkstatt",
    "mitarbeiter": "Mitarbeiter",
}
ROLE_ORDER = ["admin", "chef", "buero", "werkstatt", "mitarbeiter"]


def _perm(visible: bool, write: bool) -> dict[str, bool]:
    return {"visible": visible, "write": visible and write}


def _template(write: set[str], read: set[str], rights: set[str]) -> dict[str, Any]:
    perms: dict[str, Any] = {m: _perm(m in write or m in read, m in write) for m in MODULES}
    perms["rights"] = {r: r in rights for r in RIGHTS}
    return perms


# Vorlagen je Rolle (beim Anlegen vorbelegt, danach je Person änderbar)
ROLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "buero": _template(
        write=set(MODULES) - {"maintenance_plans"},
        read={"maintenance_plans"},
        rights={"invoices_manage"},
    ),
    "werkstatt": _template(
        # Bestellungen: Wareneingang buchen; Versenden/Stornieren braucht „Lager & Einkauf“
        write={"workshop_orders", "appointments", "customers", "vehicles", "articles", "stock",
               "stock_counts", "documents", "purchase_orders"},
        read={"maintenance_plans", "suppliers"},
        rights=set(),
    ),
    "mitarbeiter": _template(
        write={"appointments", "workshop_orders"},
        read={"customers", "vehicles", "articles", "stock", "maintenance_plans", "documents"},
        rights=set(),
    ),
}

# Wer einen Bereich lesen darf, obwohl er ihn nicht im Menü hat (Auswahllisten in anderen Bereichen),
# z. B. braucht ein Werkstattauftrag Kunden, Fahrzeuge und Artikel.
READ_ALSO: dict[str, set[str]] = {
    "customers": {"vehicles", "workshop_orders", "quotes", "invoices", "appointments", "documents"},
    "vehicles": {"customers", "workshop_orders", "quotes", "appointments", "documents", "maintenance_plans"},
    "articles": {"stock", "stock_counts", "purchase_orders", "quotes", "workshop_orders", "invoices",
                 "maintenance_plans"},
    "suppliers": {"articles", "purchase_orders", "stock"},
    "maintenance_plans": {"workshop_orders", "vehicles"},
    "appointments": {"workshop_orders", "customers"},
    "workshop_orders": {"invoices", "vehicles", "quotes"},
    "documents": {"customers", "vehicles", "workshop_orders", "maintenance_plans"},
    "stock": {"articles", "stock_counts"},
}
# Sonderrechte, die Lesezugriff auf einen Bereich mitbringen (Buchhaltung braucht Rechnungen und Kunden)
READ_BY_RIGHT: dict[str, set[str]] = {
    "invoices": {"accounting", "invoices_manage"},
    "customers": {"accounting", "dsgvo_export", "dsgvo_delete"},
}


def role_name(user) -> str:
    return getattr(getattr(user, "role", None), "name", "") or ""


def is_manager(user) -> bool:
    return role_name(user) in MANAGER_ROLES


def _stored(user) -> dict:
    """Gespeicherte Rechte; ohne eigene Einstellung gilt die Vorlage der Rolle."""
    perms = getattr(user, "permissions", None)
    if isinstance(perms, dict):
        return perms
    return ROLE_TEMPLATES.get(role_name(user), {})


def _module_entry(user, module: str) -> dict:
    entry = _stored(user).get(module)
    if not isinstance(entry, dict):
        entry = ROLE_TEMPLATES.get(role_name(user), {}).get(module)
    if not isinstance(entry, dict):
        # Unbekannte Rolle bzw. Bereich ohne Vorlage: wie bisher freigegeben
        return {"visible": True, "write": True}
    visible = entry.get("visible", True) is not False
    return {"visible": visible, "write": visible and entry.get("write", True) is not False}


def has_right(user, right: str) -> bool:
    if is_manager(user):
        return True
    rights = _stored(user).get("rights")
    if not isinstance(rights, dict) or right not in rights:
        rights = ROLE_TEMPLATES.get(role_name(user), {}).get("rights") or {}
    return rights.get(right) is True


def can_view(user, module: str) -> bool:
    """Bereich im Menü und vollständig nutzbar (lesen)."""
    return is_manager(user) or _module_entry(user, module)["visible"]


def can_read(user, module: str) -> bool:
    """Daten lesen – auch für Auswahllisten aus anderen freigegebenen Bereichen."""
    if can_view(user, module):
        return True
    if any(can_view(user, m) for m in READ_ALSO.get(module, ())):
        return True
    return any(has_right(user, r) for r in READ_BY_RIGHT.get(module, ()))


def can_write(user, module: str) -> bool:
    return is_manager(user) or _module_entry(user, module)["write"]


def effective_permissions(user) -> dict[str, Any]:
    """Was der Benutzer tatsächlich darf (für die Oberfläche)."""
    perms: dict[str, Any] = {m: {"visible": can_view(user, m), "write": can_write(user, m)} for m in MODULES}
    perms["rights"] = {r: has_right(user, r) for r in RIGHTS}
    return perms


def normalize_permissions(raw: dict | None) -> dict[str, Any] | None:
    """Eingaben aus der Benutzerverwaltung bereinigen: nur bekannte Bereiche und Rechte, nur true/false."""
    if raw is None:
        return None
    out: dict[str, Any] = {}
    for m in MODULES:
        # Nur ausdrücklich Freigegebenes zählt (fehlt ein Bereich, ist er gesperrt)
        entry = raw.get(m) if isinstance(raw.get(m), dict) else {}
        visible = entry.get("visible") is True
        out[m] = {"visible": visible, "write": visible and entry.get("write") is True}
    rights = raw.get("rights") if isinstance(raw.get("rights"), dict) else {}
    out["rights"] = {r: rights.get(r) is True for r in RIGHTS}
    return out
