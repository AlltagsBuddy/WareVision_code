"""Tests: Schema-Validierungen und Geschäftsregeln."""

import pytest
from pydantic import ValidationError


class TestRechnungsSchemas:
    def test_leere_beschreibung_verboten(self):
        from app.schemas.invoice import InvoiceItemCreate
        with pytest.raises(ValidationError):
            InvoiceItemCreate(description="", quantity=1, unit_price=10)

    def test_negativer_preis_verboten(self):
        from app.schemas.invoice import InvoiceItemCreate
        with pytest.raises(ValidationError):
            InvoiceItemCreate(description="Test", quantity=1, unit_price=-5)

    def test_menge_null_verboten(self):
        from app.schemas.invoice import InvoiceItemCreate
        with pytest.raises(ValidationError):
            InvoiceItemCreate(description="Test", quantity=0, unit_price=10)

    def test_faelligkeitsdatum_vor_rechnungsdatum(self):
        from datetime import date
        from app.schemas.invoice import InvoiceCreate
        import uuid
        with pytest.raises(ValidationError):
            InvoiceCreate(
                customer_id=uuid.uuid4(),
                invoice_date=date(2026, 6, 15),
                due_date=date(2026, 6, 10),
            )

    def test_mwst_ausserhalb_bereich(self):
        from app.schemas.invoice import InvoiceItemCreate
        with pytest.raises(ValidationError):
            InvoiceItemCreate(description="Test", quantity=1, unit_price=10, vat_rate=150)


class TestArtikelSchemas:
    def test_leerer_name_verboten(self):
        from app.schemas.article import ArticleCreate
        with pytest.raises(ValidationError):
            ArticleCreate(name="", article_number="ART-001", purchase_price=10, selling_price=15)

    def test_leere_artikelnummer_verboten(self):
        from app.schemas.article import ArticleCreate
        with pytest.raises(ValidationError):
            ArticleCreate(name="Test", article_number="", purchase_price=10, selling_price=15)

    def test_negativer_kaufpreis_verboten(self):
        from app.schemas.article import ArticleCreate
        with pytest.raises(ValidationError):
            ArticleCreate(name="Test", article_number="ART-001", purchase_price=-1, selling_price=15)


class TestWerkstattauftragSchemas:
    def test_ungültiger_status_wird_abgelehnt(self):
        from app.schemas.workshop_order import WorkshopOrderUpdate
        with pytest.raises(ValidationError):
            WorkshopOrderUpdate(status="erfunden")

    def test_gültige_statuswerte(self):
        from app.schemas.workshop_order import WorkshopOrderUpdate
        for status in ("new", "planned", "in_progress", "completed", "invoiced", "cancelled"):
            update = WorkshopOrderUpdate(status=status)
            assert update.status == status


class TestAuditLog:
    def test_login_fehlversuch_wird_geloggt(self, client, db, admin_user):
        """Fehlgeschlagene Login-Versuche werden im Audit-Log erfasst."""
        from app.models.audit_log import AuditLog

        client.post("/api/v1/auth/login", json={
            "email": "testadmin@warevision.test",
            "password": "falsch",
        })

        logs = db.query(AuditLog).filter(AuditLog.action == "login_failed").all()
        assert len(logs) >= 1

    def test_dsgvo_aktion_wird_geloggt(self, admin_client, db, sample_customer):
        """DSGVO-Löschung erzeugt Audit-Log-Eintrag."""
        from app.models.audit_log import AuditLog

        admin_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")

        logs = db.query(AuditLog).filter(
            AuditLog.action.in_(["dsgvo_delete", "dsgvo_anonymize"])
        ).all()
        assert len(logs) >= 1
