"""ZUGFeRD/Factur-X e-invoice generation."""

from datetime import datetime, timezone
from decimal import Decimal

from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.tradelines import LineItem
from drafthorse.models.party import TaxRegistration

from app.models.app_setting import AppSetting
from app.models.invoice import Invoice
from sqlalchemy.orm import Session


def _get_company_settings(db: Session) -> dict[str, str]:
    keys = ("company_name", "company_address", "company_vat_id")
    rows = db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    return {r.key: (r.value or "").strip() for r in rows}


def _get_customer_name(inv: Invoice) -> str:
    c = inv.customer
    if c.company_name:
        return c.company_name
    parts = [c.first_name or "", c.last_name or ""]
    return " ".join(parts).strip() or (c.email or "Kunde")


def _get_customer_address(inv: Invoice) -> tuple[str, str, str]:
    """Return (street, postal_code, city) from first billing address or customer."""
    for addr in inv.customer.addresses:
        if addr.address_type == "billing":
            street = f"{addr.street} {addr.house_number or ''}".strip()
            return (street, addr.postal_code, addr.city)
    return ("", "", "")


def build_zugferd_xml(db: Session, inv: Invoice) -> str:
    """Build ZUGFeRD 2.1 BASIC XML from invoice."""
    settings = _get_company_settings(db)
    company_name = settings.get("company_name") or "WareVision"
    company_address = settings.get("company_address") or ""
    company_vat = settings.get("company_vat_id") or ""

    cust_name = _get_customer_name(inv)
    cust_street, cust_postal, cust_city = _get_customer_address(inv)

    doc = Document()
    doc.context.guideline_parameter.id = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    doc.header.id = inv.invoice_number
    doc.header.type_code = "380"
    doc.header.name = "RECHNUNG"
    doc.header.issue_date_time = inv.invoice_date
    doc.header.languages.add("de")

    doc.trade.agreement.seller.name = company_name
    doc.trade.settlement.payee.name = company_name
    if company_address:
        lines = company_address.split("\n")
        doc.trade.agreement.seller.address.line_one = lines[0][:70] if lines else ""
        if len(lines) > 1:
            doc.trade.agreement.seller.address.line_two = lines[1][:70]
    doc.trade.agreement.seller.address.country_id = "DE"
    if company_vat:
        doc.trade.agreement.seller.tax_registrations.add(
            TaxRegistration(id=("VA", company_vat))
        )

    doc.trade.agreement.buyer.name = cust_name
    doc.trade.settlement.invoicee.name = cust_name
    if cust_street:
        doc.trade.agreement.buyer.address.line_one = cust_street[:70]
    if cust_postal:
        doc.trade.agreement.buyer.address.postcode = cust_postal
    if cust_city:
        doc.trade.agreement.buyer.address.city = cust_city[:35]
    doc.trade.agreement.buyer.address.country_id = "DE"
    if inv.customer.vat_id:
        doc.trade.agreement.buyer.tax_registrations.add(
            TaxRegistration(id=("VA", inv.customer.vat_id))
        )

    doc.trade.settlement.currency_code = inv.currency or "EUR"
    doc.trade.settlement.payment_means.type_code = "30"

    now = datetime.now(timezone.utc)
    doc.trade.agreement.seller_order.issue_date_time = now
    doc.trade.agreement.buyer_order.issue_date_time = now
    doc.trade.settlement.advance_payment.received_date = now
    doc.trade.agreement.customer_order.issue_date_time = now

    vat_rates_used: set[Decimal] = set()
    for item in inv.items:
        vat_rates_used.add(item.vat_rate)

    for i, item in enumerate(inv.items, 1):
        li = LineItem()
        li.document.line_id = str(i)
        li.product.name = item.description[:35] if item.description else "Position"
        li.agreement.gross.amount = item.line_total_net
        li.agreement.gross.basis_quantity = (Decimal("1.0000"), "H87")
        li.agreement.net.amount = item.line_total_net
        li.agreement.net.basis_quantity = (item.line_total_net, "EUR")
        li.delivery.billed_quantity = (item.quantity, item.unit or "H87")
        li.settlement.trade_tax.type_code = "VAT"
        li.settlement.trade_tax.category_code = "S"
        li.settlement.trade_tax.rate_applicable_percent = item.vat_rate
        li.settlement.monetary_summation.total_amount = item.line_total_net
        doc.trade.items.add(li)

    for vat_rate in sorted(vat_rates_used):
        trade_tax = ApplicableTradeTax()
        basis = sum(
            it.line_total_net for it in inv.items if it.vat_rate == vat_rate
        )
        trade_tax.calculated_amount = round(basis * vat_rate / 100, 2)
        trade_tax.basis_amount = basis
        trade_tax.type_code = "VAT"
        trade_tax.category_code = "S"
        trade_tax.rate_applicable_percent = vat_rate
        doc.trade.settlement.trade_tax.add(trade_tax)

    doc.trade.settlement.monetary_summation.line_total = inv.net_amount
    doc.trade.settlement.monetary_summation.charge_total = Decimal("0.00")
    doc.trade.settlement.monetary_summation.allowance_total = Decimal("0.00")
    doc.trade.settlement.monetary_summation.tax_basis_total = inv.net_amount
    doc.trade.settlement.monetary_summation.tax_total = inv.vat_amount
    doc.trade.settlement.monetary_summation.grand_total = inv.gross_amount
    doc.trade.settlement.monetary_summation.due_amount = inv.gross_amount

    return doc.serialize(schema=None)


def generate_zugferd_pdf(db: Session, inv: Invoice) -> bytes:
    """Generate ZUGFeRD/Factur-X PDF (PDF + embedded XML)."""
    from facturx import generate_from_binary
    from app.services.pdf import generate_invoice_pdf

    pdf_bytes = generate_invoice_pdf(db, inv)
    xml_str = build_zugferd_xml(db, inv)
    return generate_from_binary(pdf_bytes, xml_str, check_xsd=False)
