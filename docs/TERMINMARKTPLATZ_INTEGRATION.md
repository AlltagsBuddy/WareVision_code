# Terminmarktplatz → WareVision: Schritt-für-Schritt Integration

Da du Terminmarktplatz entwickelst: Hier die exakte Anleitung zur Webhook-Integration.

---

## Teil 1: WareVision einrichten

### Schritt 1.1: WareVision starten und öffentlich erreichbar machen

```powershell
cd D:\WareVision\WareVision_code
docker compose up -d --build
```

**Für lokale Tests mit ngrok:**
```powershell
& "$env:LOCALAPPDATA\ngrok-new\ngrok.exe" http 5173
```
→ Notiere die ngrok-URL (z.B. `https://abc123.ngrok-free.dev`)

**Für Produktion:** WareVision muss unter einer öffentlichen Domain laufen (z.B. `https://warevision.dein-betrieb.de`).

---

### Schritt 1.2: API-Schlüssel in WareVision anlegen

1. WareVision öffnen: `http://localhost:5173` (oder deine öffentliche URL)
2. Einloggen als Admin: `admin@warevision.local` / `admin123`
3. **Einstellungen** (Menü links) öffnen
4. Zu **Terminmarktplatz** scrollen
5. **API-Schlüssel** eintragen – z.B. eine zufällige Zeichenkette:
   ```
   tm-wv-secret-a1b2c3d4e5f6
   ```
6. **Speichern** klicken

---

### Schritt 1.3: Webhook-URL notieren

Nach dem Speichern erscheint die **Webhook-URL**:

```
https://DEINE-URL/api/v1/appointments/webhook/termin-marktplatz
```

**Beispiele:**
- Lokal mit ngrok: `https://abc123.ngrok-free.dev/api/v1/appointments/webhook/termin-marktplatz`
- Produktion: `https://warevision.dein-betrieb.de/api/v1/appointments/webhook/termin-marktplatz`

---

## Teil 2: Terminmarktplatz – Webhook implementieren

### Schritt 2.1: Konfiguration pro Werkstatt/Anbieter

Jeder WareVision-Betrieb hat seine eigene Webhook-URL und seinen eigenen API-Schlüssel. In Terminmarktplatz brauchst du pro Anbieter:

| Konfigurationsfeld | Beschreibung | Beispiel |
|-------------------|--------------|----------|
| `webhook_url` | Vollständige WareVision-Webhook-URL | `https://abc123.ngrok-free.dev/api/v1/appointments/webhook/termin-marktplatz` |
| `webhook_api_key` | Der in WareVision hinterlegte API-Schlüssel | `tm-wv-secret-a1b2c3d4e5f6` |

Diese Werte trägt der Anbieter in seinem Terminmarktplatz-Profil ein (oder du legst sie in deiner Anbieter-DB ab).

---

### Schritt 2.2: Wann den Webhook aufrufen

| Ereignis | Wann | `action` |
|----------|------|----------|
| **Neue Buchung** | Sobald ein Kunde einen Termin gebucht hat | `booking` oder weglassen |
| **Stornierung** | Sobald der Termin storniert wird | `cancel` |
| **Terminänderung** | Wenn Datum/Zeit geändert wird | `update` |

---

### Schritt 2.3: HTTP-Request

**Methode:** `POST`  
**URL:** Die konfigurierte `webhook_url`  
**Header:**

```
Content-Type: application/json
X-API-Key: <webhook_api_key>
ngrok-skip-browser-warning: 1
```

**Hinweis:** `ngrok-skip-browser-warning: 1` ist bei ngrok-URLs erforderlich, sonst blockiert ngrok die Anfrage.

**Alternativ** statt `X-API-Key`:
```
Authorization: Bearer <webhook_api_key>
```

---

### Schritt 2.4: JSON-Body – Neue Buchung

```json
{
  "external_booking_id": "tm-<eindeutige-buchungs-id>",
  "starts_at": "2025-03-20T10:00:00+01:00",
  "ends_at": "2025-03-20T11:00:00+01:00",
  "customer_first_name": "Max",
  "customer_last_name": "Mustermann",
  "customer_email": "max@example.de",
  "customer_phone": "+49 171 1234567",
  "vehicle_license_plate": "B-XX 1234",
  "vehicle_vin": "WVWZZZ3CZWE123456",
  "title": "Ölwechsel",
  "description": "Optional: Bemerkungen des Kunden"
}
```

**Pflichtfelder:**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `external_booking_id` | string | Eindeutige ID der Buchung in Terminmarktplatz (Dublettenschutz) |
| `starts_at` | string | Beginn, ISO 8601 mit Zeitzone |
| `ends_at` | string | Ende, ISO 8601 mit Zeitzone |

**Optionale Felder:**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `customer_first_name` | string | Vorname |
| `customer_last_name` | string | Nachname |
| `customer_email` | string | E-Mail (für Kunden-Zuordnung) |
| `customer_phone` | string | Telefon |
| `vehicle_license_plate` | string | Kennzeichen |
| `vehicle_vin` | string | Fahrgestellnummer |
| `title` | string | Termintitel |
| `description` | string | Bemerkungen |

**Alternative Feldnamen** (falls du andere nutzt):

| WareVision erwartet | Akzeptierte Alternativen |
|--------------------|--------------------------|
| `external_booking_id` | `booking_id`, `id`, `uuid` |
| `starts_at` | `start_time`, `start`, `date_from` |
| `ends_at` | `end_time`, `end`, `date_to` |
| `customer_first_name` | `first_name`, `vorname` |
| `customer_last_name` | `last_name`, `nachname` |
| `customer_email` | `email` |
| `customer_phone` | `phone`, `telefon` |
| `vehicle_license_plate` | `license_plate`, `kennzeichen` |
| `vehicle_vin` | `vin` |
| `description` | `notes`, `bemerkung` |

---

### Schritt 2.5: JSON-Body – Stornierung

```json
{
  "external_booking_id": "tm-<gleiche-buchungs-id-wie-bei-buchung>",
  "action": "cancel"
}
```

WareVision setzt den Termin mit dieser `external_booking_id` auf `status: cancelled`.

---

### Schritt 2.6: JSON-Body – Terminänderung

```json
{
  "external_booking_id": "tm-<gleiche-buchungs-id>",
  "action": "update",
  "starts_at": "2025-03-21T14:00:00+01:00",
  "ends_at": "2025-03-21T15:00:00+01:00"
}
```

WareVision aktualisiert Start- und Endzeit des bestehenden Termins.

---

### Schritt 2.7: Beispiel-Code (Pseudocode)

```python
# Bei neuer Buchung
def on_booking_created(booking, provider_config):
    response = requests.post(
        provider_config["webhook_url"],
        headers={
            "Content-Type": "application/json",
            "X-API-Key": provider_config["webhook_api_key"],
        },
        json={
            "external_booking_id": f"tm-{booking.id}",
            "starts_at": booking.starts_at.isoformat(),
            "ends_at": booking.ends_at.isoformat(),
            "customer_first_name": booking.customer.first_name,
            "customer_last_name": booking.customer.last_name,
            "customer_email": booking.customer.email,
            "customer_phone": booking.customer.phone,
            "vehicle_license_plate": booking.vehicle.license_plate if booking.vehicle else None,
            "vehicle_vin": booking.vehicle.vin if booking.vehicle else None,
            "title": booking.service_name or "Termin (Terminmarktplatz)",
        },
        timeout=10,
    )
    if response.status_code != 200:
        log_error(f"WareVision webhook failed: {response.status_code} {response.text}")

# Bei Stornierung
def on_booking_cancelled(booking, provider_config):
    requests.post(
        provider_config["webhook_url"],
        headers={
            "Content-Type": "application/json",
            "X-API-Key": provider_config["webhook_api_key"],
        },
        json={
            "external_booking_id": f"tm-{booking.id}",
            "action": "cancel",
        },
        timeout=10,
    )
```

---

## Teil 3: WareVision-Antworten

### Erfolg (200 OK)

WareVision antwortet mit dem angelegten/aktualisierten Termin:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "...",
  "vehicle_id": "...",
  "appointment_type": "workshop",
  "source": "termin_marktplatz",
  "status": "planned",
  "title": "Ölwechsel",
  "description": null,
  "starts_at": "2025-03-20T09:00:00Z",
  "ends_at": "2025-03-20T10:00:00Z",
  "created_at": "2025-03-15T12:00:00Z"
}
```

### Fehler

| Status | Bedeutung |
|--------|-----------|
| 400 | Ungültige oder unvollständige Daten (z.B. fehlende Pflichtfelder, falsches Datumsformat) |
| 401 | Ungültiger oder fehlender API-Schlüssel |
| 503 | WareVision: API-Schlüssel noch nicht in Einstellungen hinterlegt |

---

## Teil 4: Testen

### Schritt 4.1: Manueller Test mit curl

```powershell
$url = "https://DEINE-URL/api/v1/appointments/webhook/termin-marktplatz"
$apiKey = "tm-wv-secret-a1b2c3d4e5f6"
$body = @{
    external_booking_id = "tm-test-001"
    starts_at = "2025-03-25T14:00:00+01:00"
    ends_at = "2025-03-25T15:00:00+01:00"
    customer_first_name = "Test"
    customer_last_name = "Kunde"
    customer_email = "test@example.de"
    title = "Test-Termin"
} | ConvertTo-Json

Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Headers @{ "X-API-Key" = $apiKey } -Body $body
```

### Schritt 4.2: Prüfen in WareVision

1. **Terminplaner** öffnen
2. Termin am 25.03.2025, 14:00–15:00 prüfen
3. Quelle sollte „Terminmarktplatz“ sein

### Schritt 4.3: Storno testen

```powershell
$body = @{
    external_booking_id = "tm-test-001"
    action = "cancel"
} | ConvertTo-Json

Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Headers @{ "X-API-Key" = $apiKey } -Body $body
```

→ Termin sollte in WareVision als „storniert“ erscheinen.

---

## Teil 5: Checkliste für Terminmarktplatz

- [ ] Pro Anbieter: `webhook_url` und `webhook_api_key` speichern
- [ ] Bei Buchung: POST mit `external_booking_id`, `starts_at`, `ends_at` (+ optionale Kundendaten)
- [ ] Bei Stornierung: POST mit `external_booking_id` und `action: "cancel"`
- [ ] Bei Änderung: POST mit `external_booking_id`, `action: "update"`, `starts_at`, `ends_at`
- [ ] Header `X-API-Key` (oder `Authorization: Bearer`) setzen
- [ ] `Content-Type: application/json` setzen
- [ ] Datum/Zeit als ISO 8601 mit Zeitzone (z.B. `+01:00`)
- [ ] `external_booking_id` über alle Events hinweg stabil halten (Dublettenschutz)

---

## Datumsformat

**Gültig:**
- `2025-03-20T10:00:00+01:00`
- `2025-03-20T09:00:00Z`
- `2025-03-20T10:00:00`

**Ungültig:**
- `20.03.2025 10:00`
- `2025-03-20` (ohne Uhrzeit)

---

## Fehlersuche: Termine kommen nicht an

### 1. Verbindung prüfen (Health-Check)

```powershell
$url = "https://DEINE-WAREVISION-URL/api/v1/appointments/webhook/termin-marktplatz/health"
$apiKey = "DEIN_API_SCHLÜSSEL"
Invoke-RestMethod -Uri $url -Headers @{ "X-API-Key" = $apiKey }
```

**Erwartung:** `{"status":"ok","message":"API-Schlüssel gültig, Webhook bereit"}`

- **401:** API-Schlüssel falsch oder fehlt – prüfe Header `X-API-Key`
- **503:** API-Schlüssel in WareVision nicht hinterlegt – Einstellungen prüfen
- **Keine Antwort:** WareVision nicht erreichbar (Firewall, falsche URL, ngrok nicht aktiv)

### 2. Audit-Log in WareVision prüfen

**WareVision** → **Audit-Log** → Filter **Aktion** → „Terminmarktplatz: …“

- **Import/Storno/Update:** Webhook wurde verarbeitet
- **Fehler:** Webhook kam an, aber Payload war ungültig – `new_values` zeigt Details

### 3. Backend-Logs prüfen

```powershell
docker compose logs backend -f
```

Bei jedem Webhook-Aufruf erscheinen Meldungen wie:
- `Terminmarktplatz webhook received: external_id=...`
- `Terminmarktplatz: Termin importiert external_id=...`
- Bei Fehlern: `external_booking_id fehlt`, `Datumsparsing fehlgeschlagen`, etc.

### 4. Häufige Ursachen

| Problem | Lösung |
|---------|--------|
| WareVision nur lokal (localhost) | ngrok oder öffentliche Domain nutzen – Terminmarktplatz-Server muss die URL erreichen |
| API-Schlüssel stimmt nicht | Exakt gleichen Schlüssel in beiden Systemen verwenden (keine Leerzeichen) |
| Falsches Datumsformat | ISO 8601 mit Zeitzone, z.B. `2025-03-20T10:00:00+01:00` |
| Payload in `data` oder `booking` gewrappt | Wird unterstützt – WareVision erkennt `payload.data` und `payload.booking` |
