# Terminmarktplatz: Buchungen kommen nicht an – Vollständige Fehlersuche

URL und API-Schlüssel sind hinterlegt, aber Termine erscheinen nicht im WareVision-Terminplaner. Diese Checkliste hilft, die Ursache zu finden.

---

## Teil 1: WareVision prüfen

### 1.1 Verbindung testen (ohne API-Key)

```powershell
Invoke-RestMethod -Uri "https://IHRE-URL/api/v1/appointments/webhook/termin-marktplatz/ping"
```

**Erwartung:** `{"status":"ok","message":"WareVision Webhook erreichbar"}`

| Ergebnis | Bedeutung |
|----------|-----------|
| Erfolg | WareVision ist erreichbar, Routing funktioniert |
| Timeout/Fehler | WareVision nicht erreichbar – Firewall, ngrok nicht aktiv, falsche URL |
| 404 | Falscher Pfad – URL prüfen (muss `/api/v1/appointments/webhook/termin-marktplatz` enthalten) |

### 1.2 API-Schlüssel prüfen

```powershell
$headers = @{ "X-API-Key" = "IHRE-API-SCHLÜSSEL" }
Invoke-RestMethod -Uri "https://IHRE-URL/api/v1/appointments/webhook/termin-marktplatz/health" -Headers $headers
```

**Erwartung:** `{"status":"ok","message":"API-Schlüssel gültig, Webhook bereit"}`

| Ergebnis | Bedeutung |
|----------|-----------|
| 401 | API-Schlüssel falsch oder fehlt – exakt mit WareVision Einstellungen vergleichen |
| 503 | API-Schlüssel in WareVision nicht hinterlegt |

### 1.3 Test-Buchung senden

```powershell
.\scripts\test-terminmarktplatz-webhook.ps1 -BaseUrl "https://IHRE-URL" -ApiKey "IHRE-API-SCHLÜSSEL"
```

- Wenn **alle drei Schritte** erfolgreich sind und der Test-Termin im Planer erscheint → WareVision ist korrekt konfiguriert. Das Problem liegt bei **Terminmarktplatz**.
- Wenn der Test funktioniert, aber echte Buchungen nicht ankommen → Terminmarktplatz sendet den Webhook nicht oder mit anderem Format.

### 1.4 Audit-Log prüfen

**WareVision** → **Audit-Log** → Filter **Aktion** auf „Terminmarktplatz“ setzen.

| Aktion | Bedeutung |
|--------|-----------|
| `webhook_termin_marktplatz_import` | Buchung kam an und wurde verarbeitet |
| `webhook_termin_marktplatz_error` | Webhook kam an, Payload war ungültig – `new_values` zeigt empfangene Keys und Fehler |
| Keine Einträge | Webhook erreicht WareVision gar nicht (401/503 vor Log, oder Terminmarktplatz sendet nicht) |

### 1.5 Backend-Logs prüfen

```powershell
docker compose logs backend -f
```

Bei jedem Webhook-Aufruf erscheinen Meldungen wie:
- `Terminmarktplatz webhook POST received, payload keys=[...]` → Webhook erreicht WareVision
- `Terminmarktplatz: Termin importiert external_id=...` → Erfolg
- `external_booking_id fehlt`, `Datumsparsing fehlgeschlagen` etc. → Payload-Problem

---

## Teil 2: Terminmarktplatz prüfen

### 2.1 Wird der Webhook überhaupt aufgerufen?

- **Wo** im Code wird der Webhook nach einer Buchung ausgelöst?
- Wird er **synchron** direkt nach dem Speichern der Buchung aufgerufen, oder **asynchron** (Queue, Cron)?
- Wenn asynchron: Läuft der Job? Gibt es Fehler in den Terminmarktplatz-Logs?

### 2.2 HTTP-Request – Alle Punkte prüfen

| Prüfpunkt | Erforderlich | Beispiel |
|-----------|--------------|----------|
| **Methode** | POST | `POST` (nicht GET) |
| **URL** | Vollständig | `https://abc123.ngrok-free.dev/api/v1/appointments/webhook/termin-marktplatz` |
| **Content-Type** | application/json | `Content-Type: application/json` |
| **X-API-Key** | Header mit Schlüssel | `X-API-Key: tm-wv-secret-12345` |
| **Bei ngrok** | Zusätzlicher Header | `ngrok-skip-browser-warning: 1` |
| **Body** | Gültiges JSON | Siehe 2.3 |

### 2.3 JSON-Body – Pflichtfelder

Der Body **muss** diese Felder enthalten (oder unterstützte Alternativen):

| Pflichtfeld | Akzeptierte Feldnamen | Beispiel |
|-------------|----------------------|----------|
| Buchungs-ID | `external_booking_id`, `externalBookingId`, `booking_id`, `bookingId`, `id`, `uuid` | `"tm-12345"` |
| Startzeit | `starts_at`, `startsAt`, `start_time`, `startTime`, `start`, `date_from`, `dateFrom` | `"2025-03-20T10:00:00+01:00"` |
| Endzeit | `ends_at`, `endsAt`, `end_time`, `endTime`, `end`, `date_to`, `dateTo` | `"2025-03-20T11:00:00+01:00"` |

**Datumsformat:** ISO 8601, z.B. `2025-03-20T10:00:00+01:00` oder `2025-03-20T10:00:00Z`. Auch Unix-Zeitstempel (Sekunden oder Millisekunden) werden akzeptiert.

**Ungültig:** `20.03.2025 10:00`, `2025-03-20` (ohne Uhrzeit)

### 2.4 Verschachtelter Payload

WareVision unterstützt gewrappte Payloads:

```json
{ "data": { "external_booking_id": "...", "starts_at": "...", "ends_at": "..." } }
```
oder
```json
{ "booking": { "external_booking_id": "...", "starts_at": "...", "ends_at": "..." } }
```

Die Pflichtfelder müssen innerhalb von `data` bzw. `booking` liegen.

### 2.5 Fehlerantwort auswerten

Wenn WareVision mit **400** antwortet, enthält die Antwort Details:

```json
{
  "detail": {
    "error": "Ungültige oder unvollständige Buchungsdaten",
    "hint": "Pflichtfelder: external_booking_id, starts_at, ends_at ...",
    "received_keys": ["data", "booking"],
    "received_starts_at": null,
    "received_ends_at": null
  }
}
```

- `received_keys`: Welche Keys waren im **Root**-Payload? Bei Wrapper muss die eigentliche Buchung in `data`/`booking` sein.
- `received_starts_at` / `received_ends_at`: Wurden Datumswerte erkannt? Wenn `null` → Feldnamen oder Format prüfen.

### 2.6 Terminmarktplatz-Logs

- Wird der Webhook-Code überhaupt ausgeführt?
- Welche HTTP-Status-Code kommt zurück? (200 = OK, 400 = Fehler im Payload, 401 = API-Key, 503 = nicht konfiguriert)
- Wird die Fehlerantwort (Body) geloggt?
- Gibt es Timeout/Netzwerkfehler?

---

## Teil 3: Schnelltest

**Schritt 1:** Test-Script ausführen:
```powershell
.\scripts\test-terminmarktplatz-webhook.ps1 -BaseUrl "https://IHRE-URL" -ApiKey "IHRE-API-SCHLÜSSEL"
```

**Schritt 2:** Terminplaner öffnen – erscheint der Test-Termin?

- **Ja** → WareVision ist in Ordnung. Terminmarktplatz sendet nicht oder mit falschem Format. Teil 2 prüfen.
- **Nein** → Teil 1 prüfen (Verbindung, API-Key, Audit-Log, Backend-Logs).

---

## Teil 4: Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| Keine Einträge im Audit-Log | Webhook erreicht WareVision nicht | 401/503 vor Verarbeitung; Terminmarktplatz sendet nicht; falsche URL; Firewall |
| `external_booking_id fehlt` | Feld fehlt oder heißt anders | Eines der akzeptierten Felder verwenden, bei Wrapper in `data`/`booking` |
| `Datumsparsing fehlgeschlagen` | Datumsformat ungültig | ISO 8601 mit Uhrzeit, z.B. `2025-03-20T10:00:00+01:00` |
| Test funktioniert, echte Buchungen nicht | Webhook wird nicht aufgerufen | Terminmarktplatz: Aufruf nach Buchung implementieren/prüfen |
| ngrok: 502 Bad Gateway | ngrok blockiert | Header `ngrok-skip-browser-warning: 1` mitsenden |
