"""Tests: Dokumentenmanagement."""

import io


def _pdf_bytes() -> bytes:
    """Minimales gültiges PDF."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f\ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF"


class TestDokumenteUpload:
    def test_pdf_hochladen(self, admin_client):
        """PDF-Dokument hochladen."""
        res = admin_client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["filename"] == "test.pdf"
        assert data["content_type"] == "application/pdf"

    def test_pdf_mit_kundenzuordnung(self, admin_client, sample_customer):
        """PDF einem Kunden zuordnen."""
        res = admin_client.post(
            "/api/v1/documents",
            files={"file": ("kunde.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            data={"customer_id": str(sample_customer.id)},
        )
        assert res.status_code == 201
        assert res.json()["customer_id"] == str(sample_customer.id)

    def test_pdf_mit_fahrzeugzuordnung(self, admin_client, sample_vehicle):
        """PDF einem Fahrzeug zuordnen."""
        res = admin_client.post(
            "/api/v1/documents",
            files={"file": ("fzg.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            data={"vehicle_id": str(sample_vehicle.id)},
        )
        assert res.status_code == 201
        assert res.json()["vehicle_id"] == str(sample_vehicle.id)

    def test_unerlaubter_dateityp_abgelehnt(self, admin_client):
        """ZIP-Datei → 400."""
        res = admin_client.post(
            "/api/v1/documents",
            files={"file": ("archiv.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
        )
        assert res.status_code == 400

    def test_bild_hochladen(self, admin_client):
        """JPEG-Datei hochladen."""
        jpeg = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 16 + bytes([0xFF, 0xD9])
        res = admin_client.post(
            "/api/v1/documents",
            files={"file": ("foto.jpg", io.BytesIO(jpeg), "image/jpeg")},
        )
        assert res.status_code == 201


class TestDokumenteVerwaltung:
    def _upload(self, client):
        return client.post(
            "/api/v1/documents",
            files={"file": ("doc.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        ).json()

    def test_dokument_liste(self, admin_client):
        """Dokumentenliste abrufen."""
        self._upload(admin_client)
        res = admin_client.get("/api/v1/documents")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_dokument_abrufen(self, admin_client):
        """Einzelnes Dokument abrufen."""
        doc = self._upload(admin_client)
        res = admin_client.get(f"/api/v1/documents/{doc['id']}")
        assert res.status_code == 200
        assert res.json()["id"] == doc["id"]

    def test_dokument_herunterladen(self, admin_client):
        """Dokument-Download liefert Dateiinhalt."""
        doc = self._upload(admin_client)
        res = admin_client.get(f"/api/v1/documents/{doc['id']}/download")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/pdf")

    def test_dokument_aktualisieren(self, admin_client, sample_customer):
        """Dokument einem Kunden zuordnen (PATCH)."""
        doc = self._upload(admin_client)
        res = admin_client.patch(f"/api/v1/documents/{doc['id']}", json={
            "customer_id": str(sample_customer.id),
        })
        assert res.status_code == 200
        assert res.json()["customer_id"] == str(sample_customer.id)

    def test_dokument_loeschen_werkstatt_verboten(self, werkstatt_client):
        """Werkstatt-Benutzer darf keine Dokumente löschen."""
        doc = self._upload(werkstatt_client)
        res = werkstatt_client.delete(f"/api/v1/documents/{doc['id']}")
        assert res.status_code in (403, 401)

    def test_dokument_loeschen_admin(self, admin_client):
        """Admin darf Dokumente löschen."""
        doc = self._upload(admin_client)
        res = admin_client.delete(f"/api/v1/documents/{doc['id']}")
        assert res.status_code == 204

    def test_unbekanntes_dokument_404(self, admin_client):
        """Unbekannte Dokument-ID → 404."""
        res = admin_client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404
