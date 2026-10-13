"""Tests: E-Mail-Versand (Unit- und API-Tests mit Mock)."""

from unittest.mock import MagicMock, patch

import pytest


class TestEmailAPI:
    def test_test_email_ohne_empfaenger(self, admin_client, db):
        """Kein Empfänger und keine company_email → 400."""
        res = admin_client.post("/api/v1/settings/test-email", json={})
        assert res.status_code == 400
        assert "Empfänger" in res.json()["detail"] or "empf" in res.json()["detail"].lower()

    def test_test_email_werkstatt_verboten(self, werkstatt_client):
        """Werkstatt-Benutzer darf keine Test-E-Mail senden."""
        res = werkstatt_client.post("/api/v1/settings/test-email", json={
            "recipient_email": "test@example.com",
        })
        assert res.status_code in (401, 403)

    def test_test_email_nicht_authentifiziert(self, client):
        """Kein Token → 401/403."""
        res = client.post("/api/v1/settings/test-email", json={
            "recipient_email": "test@example.com",
        })
        assert res.status_code in (401, 403)

    def test_test_email_mit_mock(self, admin_client):
        """Mit gemocktem send_email: Endpunkt gibt Erfolgsmeldung zurück."""
        with patch("app.services.email.send_email") as mock_send:
            mock_send.return_value = None
            res = admin_client.post("/api/v1/settings/test-email", json={
                "recipient_email": "empfaenger@example.com",
            })
        assert res.status_code == 200
        data = res.json()
        assert "empfaenger@example.com" in data["recipient"]
        mock_send.assert_called_once()

    def test_test_email_company_email_fallback(self, admin_client, db):
        """company_email aus Einstellungen als Fallback-Empfänger."""
        from app.models.app_setting import AppSetting
        setting = db.query(AppSetting).filter(AppSetting.key == "company_email").first()
        if setting:
            setting.value = "firma@example.com"
        else:
            db.add(AppSetting(key="company_email", value="firma@example.com"))
        db.flush()

        with patch("app.services.email.send_email") as mock_send:
            mock_send.return_value = None
            res = admin_client.post("/api/v1/settings/test-email", json={})
        assert res.status_code == 200
        assert res.json()["recipient"] == "firma@example.com"


class TestEmailServiceUnit:
    def test_termin_bestaetigung_smtp(self):
        """send_appointment_confirmation ruft send_email auf."""
        from app.services.email import send_appointment_confirmation

        db_mock = MagicMock()

        with patch("app.services.email.send_email") as mock_send:
            mock_send.return_value = None
            send_appointment_confirmation(
                db_mock,
                to_email="kunde@example.com",
                customer_name="Max Mustermann",
                title="Reifenwechsel",
                starts_at="Mo, 01.06.2026, 09:00 Uhr",
                ends_at="Mo, 01.06.2026, 11:00 Uhr",
            )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "kunde@example.com"
        assert "Terminbestätigung" in call_kwargs["subject"]

    def test_termin_stornierung_smtp(self):
        """send_appointment_cancellation ruft send_email auf."""
        from app.services.email import send_appointment_cancellation

        db_mock = MagicMock()

        with patch("app.services.email.send_email") as mock_send:
            mock_send.return_value = None
            send_appointment_cancellation(
                db_mock,
                to_email="kunde@example.com",
                customer_name="Max Mustermann",
                title="Probefahrt",
                starts_at="Di, 02.06.2026, 14:00 Uhr",
            )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "kunde@example.com"
        assert "absage" in call_kwargs["subject"].lower() or "storn" in call_kwargs["subject"].lower()

    def test_send_email_resend_bevorzugt(self, db):
        """send_email nutzt Resend wenn API-Key vorhanden."""
        from app.services.email import send_email

        with patch("app.services.email._get_resend_settings") as mock_rs, \
             patch("app.services.email._send_via_resend") as mock_resend, \
             patch("app.services.email._send_via_smtp") as mock_smtp:
            mock_rs.return_value = {
                "resend_api_key": "re_testkey",
                "resend_from_email": "noreply@example.com",
                "resend_from_name": "Test",
            }
            mock_resend.return_value = None

            send_email(
                db,
                to_email="test@example.com",
                subject="Test",
                text_body="Hallo",
            )

        mock_resend.assert_called_once()
        mock_smtp.assert_not_called()

    def test_send_email_smtp_fallback(self, db):
        """send_email fällt auf SMTP zurück wenn kein Resend-Key."""
        from app.services.email import send_email

        with patch("app.services.email._get_resend_settings") as mock_rs, \
             patch("app.services.email._send_via_smtp") as mock_smtp:
            mock_rs.return_value = {"resend_api_key": ""}
            mock_smtp.return_value = None

            send_email(
                db,
                to_email="test@example.com",
                subject="Test",
                text_body="Hallo",
            )

        mock_smtp.assert_called_once()
