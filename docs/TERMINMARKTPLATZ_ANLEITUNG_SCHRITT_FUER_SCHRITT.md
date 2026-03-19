# Terminmarktplatz → WareVision: Genaue Schritt-für-Schritt-Anleitung

**Was genau wo machen.** Jeder Schritt mit exaktem Ort und exakter Aktion.

---

## Phase A: WareVision vorbereiten

### Schritt A1: WareVision starten

| Wo | Was |
|----|-----|
| **Ort** | PowerShell, Projektordner |
| **Befehl** | `cd D:\WareVision\WareVision_code` |
| **Dann** | `docker compose up -d --build` |
| **Warten** | Bis „Started“ erscheint |

---

### Schritt A2: Öffentliche URL bereitstellen (wichtig)

Wenn WareVision nur auf `localhost` läuft, kann Terminmarktplatz (auf einem anderen Server) nicht darauf zugreifen.

**Option 1 – ngrok (für Tests):**

| Wo | Was |
|----|-----|
| **Ort** | Neues PowerShell-Fenster |
| **Befehl** | `& "$env:LOCALAPPDATA\ngrok-new\ngrok.exe" http 5173` |
| **Notieren** | Die URL in der Zeile „Forwarding“, z.B. `https://abc123.ngrok-free.dev` |
| **Fenster** | Offen lassen (ngrok muss laufen) |

**Option 2 – Produktion:** WareVision muss unter einer öffentlichen Domain laufen (z.B. `https://warevision.deine-domain.de`).

---

### Schritt A3: API-Schlüssel in WareVision anlegen

| Wo | Was |
|----|-----|
| **Ort** | Webbrowser |
| **URL** | `http://localhost:5173` (oder deine ngrok-URL) |
| **Login** | E-Mail: `admin@warevision.local` |
| **Login** | Passwort: `admin123` |

| Wo | Was |
|----|-----|
| **Ort** | WareVision, linke Menüleiste |
| **Klicken** | „Einstellungen“ |

| Wo | Was |
|----|-----|
| **Ort** | Einstellungsseite, nach unten scrollen |
| **Bereich** | „Terminmarktplatz“ |
| **Feld** | „API-Schlüssel“ |
| **Eingeben** | Einen geheimen Schlüssel, z.B. `tm-wv-secret-12345` |
| **Wichtig** | Kein Leerzeichen, kein Sonderzeichen das Probleme macht |

| Wo | Was |
|----|-----|
| **Ort** | Unten auf der Seite |
| **Klicken** | „Speichern“ |

---

### Schritt A4: Webhook-URL kopieren

| Wo | Was |
|----|-----|
| **Ort** | Einstellungsseite, nach dem Speichern |
| **Erscheint** | Ein grauer Kasten mit „Webhook-URL für Terminmarktplatz:“ |
| **Darin** | Eine URL wie `https://abc123.ngrok-free.dev/api/v1/appointments/webhook/termin-marktplatz` |
| **Aktion** | Diese URL komplett kopieren (Strg+C) |
| **Notieren** | Auch den API-Schlüssel (den du in Schritt A3 eingegeben hast) |

---

## Phase B: Terminmarktplatz konfigurieren

### Schritt B1: Daten für den Anbieter speichern

| Wo | Was |
|----|-----|
| **Ort** | Terminmarktplatz – Datenbank oder Konfiguration des Anbieters (Werkstatt) |
| **Speichern** | Zwei Werte pro Anbieter: |

| Feld | Wert (Beispiel) | Woher |
|------|-----------------|-------|
| `webhook_url` | `https://abc123.ngrok-free.dev/api/v1/appointments/webhook/termin-marktplatz` | Aus Schritt A4 |
| `webhook_api_key` | `tm-wv-secret-12345` | Aus Schritt A3 |

---

### Schritt B2: Bei Buchung – Webhook aufrufen

| Wo | Was |
|----|-----|
| **Ort** | Terminmarktplatz – Code, der ausgeführt wird, wenn ein Kunde einen Termin bucht |
| **Wann** | Direkt nach der Buchung (z.B. in der Funktion, die die Buchung speichert) |

**HTTP-Request:**

| Eigenschaft | Wert |
|-------------|------|
| **Methode** | `POST` |
| **URL** | Die gespeicherte `webhook_url` |
| **Header 1** | `Content-Type: application/json` |
| **Header 2** | `X-API-Key: <webhook_api_key>` (z.B. `X-API-Key: tm-wv-secret-12345`) |
| **Body** | JSON (siehe unten) |

**JSON-Body (Beispiel):**

```json
{
  "external_booking_id": "tm-12345",
  "starts_at": "2025-03-20T10:00:00+01:00",
  "ends_at": "2025-03-20T11:00:00+01:00",
  "customer_first_name": "Max",
  "customer_last_name": "Mustermann",
  "customer_email": "max@example.de",
  "customer_phone": "+49 171 1234567",
  "vehicle_license_plate": "B-XX 1234",
  "title": "Ölwechsel"
}
```

**Pflichtfelder (müssen immer vorhanden sein):**

| Feld | Beispiel | Beschreibung |
|------|----------|--------------|
| `external_booking_id` | `"tm-12345"` | Eindeutige ID der Buchung in deinem System |
| `starts_at` | `"2025-03-20T10:00:00+01:00"` | Beginn, ISO 8601 mit Zeitzone |
| `ends_at` | `"2025-03-20T11:00:00+01:00"` | Ende, ISO 8601 mit Zeitzone |

---

### Schritt B3: Bei Stornierung – Webhook aufrufen

| Wo | Was |
|----|-----|
| **Ort** | Terminmarktplatz – Code, der ausgeführt wird, wenn ein Termin storniert wird |

**JSON-Body:**

```json
{
  "external_booking_id": "tm-12345",
  "action": "cancel"
}
```

`external_booking_id` muss dieselbe sein wie bei der Buchung.

---

## Phase C: Testen

### Schritt C1: Health-Check (Verbindung prüfen)

| Wo | Was |
|----|-----|
| **Ort** | PowerShell |
| **URL** | Ersetze `DEINE-URL` und `DEIN-SCHLÜSSEL` durch deine Werte |

```powershell
$url = "https://DEINE-URL/api/v1/appointments/webhook/termin-marktplatz/health"
$apiKey = "DEIN-SCHLÜSSEL"
Invoke-RestMethod -Uri $url -Headers @{ "X-API-Key" = $apiKey }
```

**Erwartete Ausgabe:** `status ok message API-Schlüssel gültig, Webhook bereit`

**Wenn Fehler:**
- **401** → API-Schlüssel falsch oder fehlt
- **503** → API-Schlüssel in WareVision nicht hinterlegt
- **Keine Antwort** → WareVision nicht erreichbar (ngrok nicht aktiv? URL falsch?)

---

### Schritt C2: Test-Buchung senden

| Wo | Was |
|----|-----|
| **Ort** | PowerShell |

```powershell
$url = "https://DEINE-URL/api/v1/appointments/webhook/termin-marktplatz"
$apiKey = "DEIN-SCHLÜSSEL"
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

**Erwartung:** Es wird ein JSON-Objekt mit dem angelegten Termin zurückgegeben.

---

### Schritt C3: Prüfen in WareVision

| Wo | Was |
|----|-----|
| **Ort** | WareVision im Browser |
| **Menü** | Links „Terminplaner“ anklicken |
| **Prüfen** | Termin am 25.03.2025, 14:00–15:00 |
| **Prüfen** | Quelle sollte „Terminmarktplatz“ sein |

---

### Schritt C4: Audit-Log prüfen (optional)

| Wo | Was |
|----|-----|
| **Ort** | WareVision, linke Menüleiste |
| **Klicken** | „Audit-Log“ |
| **Filter** | Aktion: „Terminmarktplatz: Import“ |
| **Prüfen** | Es sollte ein Eintrag zur Test-Buchung erscheinen |

---

## Kurz-Checkliste

**WareVision:**
- [ ] Schritt A1: WareVision gestartet
- [ ] Schritt A2: ngrok oder öffentliche URL aktiv
- [ ] Schritt A3: API-Schlüssel in Einstellungen hinterlegt
- [ ] Schritt A4: Webhook-URL notiert

**Terminmarktplatz:**
- [ ] Schritt B1: `webhook_url` und `webhook_api_key` pro Anbieter gespeichert
- [ ] Schritt B2: Bei Buchung POST mit `external_booking_id`, `starts_at`, `ends_at` (+ Kundendaten)
- [ ] Schritt B3: Bei Stornierung POST mit `external_booking_id` und `action: "cancel"`
- [ ] Header `X-API-Key` wird gesetzt
- [ ] Header `Content-Type: application/json` wird gesetzt

**Test:**
- [ ] Schritt C1: Health-Check erfolgreich
- [ ] Schritt C2: Test-Buchung senden
- [ ] Schritt C3: Termin erscheint im Terminplaner
