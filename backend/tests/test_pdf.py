"""Tests: PDF-Generierung (Smoke-Tests)."""

from datetime import date
from decimal import Decimal

import pytest


class TestRechnungsPDF:
    def test_rechnung_pdf_generierung(self, db, sample_invoice):
        """Rechnungs-PDF wird ohne Fehler generiert und hat Mindestgröße."""
        from app.services.pdf import generate_invoice_pdf

        pdf_bytes = generate_invoice_pdf(db, sample_invoice)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        # PDF-Magic-Bytes prüfen
        assert pdf_bytes[:4] == b"%PDF"

    def test_rechnung_pdf_mit_logo(self, db, sample_invoice):
        """PDF-Generierung funktioniert auch wenn kein Logo hinterlegt ist."""
        from app.services.pdf import generate_invoice_pdf

        # Kein Logo gesetzt → kein Fehler
        pdf_bytes = generate_invoice_pdf(db, sample_invoice)
        assert pdf_bytes[:4] == b"%PDF"


class TestMahnbrief:
    def test_mahnbrief_stufe_1(self, db, sample_invoice):
        """Mahnbrief Stufe 1 (Zahlungserinnerung) wird korrekt generiert."""
        from app.services.pdf import generate_reminder_pdf

        sample_invoice.reminder_level = 1
        db.flush()

        pdf_bytes = generate_reminder_pdf(db, sample_invoice)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 500

    def test_mahnbrief_stufe_2(self, db, sample_invoice):
        """1. Mahnung PDF generieren."""
        from app.services.pdf import generate_reminder_pdf

        sample_invoice.reminder_level = 2
        db.flush()
        pdf_bytes = generate_reminder_pdf(db, sample_invoice)
        assert pdf_bytes[:4] == b"%PDF"

    def test_mahnbrief_stufe_3(self, db, sample_invoice):
        """2. Mahnung (letzte Mahnung) PDF generieren."""
        from app.services.pdf import generate_reminder_pdf

        sample_invoice.reminder_level = 3
        db.flush()
        pdf_bytes = generate_reminder_pdf(db, sample_invoice)
        assert pdf_bytes[:4] == b"%PDF"

    def test_mahnbrief_fallback_bei_level_0(self, db, sample_invoice):
        """generate_reminder_pdf behandelt level=0 als Stufe 1."""
        from app.services.pdf import generate_reminder_pdf

        sample_invoice.reminder_level = 0
        db.flush()
        # Sollte nicht werfen sondern Stufe 1 generieren
        pdf_bytes = generate_reminder_pdf(db, sample_invoice)
        assert pdf_bytes[:4] == b"%PDF"


class TestWerkstattauftragPDF:
    def test_werkstattauftrag_pdf(self, db, sample_customer, sample_vehicle, admin_user):
        """Werkstattauftrag-PDF Smoke-Test."""
        from app.services.pdf import generate_workshop_order_pdf
        from app.models.workshop_order import WorkshopOrder

        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-TEST-0001",
            status="new",
            complaint_description="Motor läuft unrund",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        pdf_bytes = generate_workshop_order_pdf(db, order)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
