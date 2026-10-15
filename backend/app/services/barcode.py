"""Barcode-Hilfen (EAN/GTIN/UPC) für Artikel und Lieferanten-Artikeldaten."""


def clean_barcode(code: str | None) -> str | None:
    """Barcode vereinheitlichen: Leerzeichen entfernen; leer → None."""
    if code is None:
        return None
    code = "".join(str(code).split())
    return code or None


def barcode_variants(code: str) -> list[str]:
    """Gleiche Ware kann als UPC-A (12 Ziffern) oder EAN-13 mit führender 0 gescannt werden."""
    code = clean_barcode(code) or ""
    variants = {code}
    if code.isdigit():
        if len(code) == 12:
            variants.add("0" + code)
        if len(code) == 13 and code.startswith("0"):
            variants.add(code[1:])
    return [v for v in variants if v]


def looks_like_gtin(code: str | None) -> bool:
    """GTIN-8/12/13/14 (nur Ziffern)."""
    c = clean_barcode(code) or ""
    return c.isdigit() and len(c) in (8, 12, 13, 14)
