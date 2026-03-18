# WareVision – Test-Zugang

Diese Anleitung ermöglicht das einfache Testen der Warenwirtschaft von verschiedenen Systemen (PC, Tablet, Smartphone, andere Netzwerke) mit **Link + Zugangsdaten**.

---

## Schnellstart

### 1. Link

| Umgebung | URL |
|----------|-----|
| **Lokal (Docker)** | http://localhost:5173 |
| **Lokal (Dev)** | http://localhost:5173 |
| **Im Netzwerk** | http://\<SERVER-IP\>:5173 |

> **Hinweis:** Ersetze `\<SERVER-IP\>` durch die IP-Adresse des Rechners, auf dem WareVision läuft (z.B. `http://192.168.1.100:5173`).

### 2. Zugangsdaten

| Rolle | E-Mail | Passwort |
|-------|--------|----------|
| **Admin** | admin@warevision.local | admin123 |
| **Werkstatt** | *(nach Anlegen)* | *(nach Anlegen)* |

---

## Login-Link mit vorausgefüllter E-Mail

Für Tester kann ein Link erstellt werden, der die E-Mail bereits vorausfüllt (Passwort aus Sicherheitsgründen weiterhin manuell eingeben):

```
http://localhost:5173/login?email=admin@warevision.local
```

Oder mit Server-IP:

```
http://192.168.1.100:5173/login?email=admin@warevision.local
```

---

## Zugriff aus dem Netzwerk

### Docker

1. WareVision starten: `docker compose up -d --build`
2. IP-Adresse des Rechners ermitteln (z.B. `ipconfig` unter Windows)
3. Andere Geräte im gleichen Netzwerk können über `http://<IP>:5173` zugreifen

### Firewall

Stelle sicher, dass die Ports **5173** (Frontend) und **8000** (API, falls direkt genutzt) in der Firewall freigegeben sind.

---

## Zugriff über Internet (ngrok)

Mit ngrok kannst du einen **öffentlichen Link** erstellen, über den WareVision von überall auf der Welt erreichbar ist (z.B. Smartphone unterwegs, Kunde, externe Tester).

### Schritt 1: ngrok installieren

1. Öffne: https://ngrok.com/download
2. Lade ngrok für Windows herunter
3. Entpacke die ZIP-Datei (z.B. nach `C:\ngrok` oder `C:\Users\<DEIN-NAME>\Downloads`)
4. Optional: Lege den ngrok-Ordner in den PATH, damit du `ngrok` von überall aufrufen kannst

**Alternativ mit winget (PowerShell als Admin):**
```powershell
winget install ngrok.ngrok
```

### Schritt 2: ngrok-Account (einmalig)

1. Gehe zu https://dashboard.ngrok.com/signup
2. Erstelle einen kostenlosen Account
3. Unter https://dashboard.ngrok.com/get-started/your-authtoken findest du deinen Authtoken
4. In der PowerShell ausführen:
   ```powershell
   ngrok config add-authtoken DEIN_AUTHTOKEN
   ```
   (Ersetze `DEIN_AUTHTOKEN` durch den Token aus dem Dashboard)

### Schritt 3: WareVision starten

Im Projektordner `D:\WareVision\WareVision_code`:

```powershell
docker compose up -d --build
```

Warte, bis alle Container laufen.

### Schritt 4: ngrok starten

**Neues PowerShell-Fenster** öffnen, dann:

```powershell
ngrok http 5173
```

Oder, wenn ngrok nicht im PATH liegt, mit vollem Pfad:

```powershell
C:\path\to\ngrok.exe http 5173
```

### Schritt 5: Link kopieren

Im ngrok-Fenster erscheint eine Ausgabe wie:

```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:5173
```

**Dein Link:** `https://abc123.ngrok-free.app`

- **Login:** `https://abc123.ngrok-free.app/login`
- **Login mit vorausgefüllter E-Mail:** `https://abc123.ngrok-free.app/login?email=admin@warevision.local`
- **Registrierung:** `https://abc123.ngrok-free.app/register`

### Schritt 6: Link teilen

Kopiere den Link und sende ihn per E-Mail, WhatsApp oder wo auch immer. Der Empfänger öffnet ihn im Browser – fertig.

**Hinweis:** Die kostenlose ngrok-Version erzeugt bei jedem Start eine neue URL. Für eine feste URL brauchst du einen kostenpflichtigen Plan.

### Weiße/leere Seite? – ngrok „Visit Site“ anklicken

Bei der **kostenlosen ngrok-Version** erscheint beim ersten Besuch eine Zwischenseite von ngrok. Sie kann wie eine leere weiße Seite wirken.

**Lösung:**  
1. Auf der Seite nach **„Visit Site“** oder **„Besuchen“** suchen – oft ein kleiner Button unten oder in der Mitte.  
2. **Einmal darauf klicken** – danach wird ein Cookie gesetzt und die App lädt normal.  
3. Falls nichts zu sehen ist: **Strg+F5** (Hard Refresh) oder die Seite in einem **Inkognito-Fenster** öffnen, dann erneut nach dem Button suchen.

Ohne Klick auf „Visit Site“ wird die eigentliche App nicht geladen – das ist eine Sicherheitsfunktion von ngrok.

---

## CORS für externe Domains (optional)

Wenn Frontend und Backend auf **verschiedenen Domains** laufen, müssen zusätzliche CORS-Origins konfiguriert werden.

**Backend `.env` oder Docker-Umgebung:**

```env
# Zusätzliche erlaubte Origins (kommagetrennt)
CORS_ORIGINS_EXTRA=https://test.warevision.de,http://192.168.1.100:5173
```

---

## Link teilen – neue Benutzer anlegen

Du kannst einen Link teilen, über den sich neue Benutzer selbst registrieren können:

**Registrierungs-Link:** `http://<DEINE-URL>/register`

Beispiel: `http://192.168.1.100:5173/register`

Der Empfänger:
1. Öffnet den Link
2. Legt ein Konto an (E-Mail, Name, Passwort)
3. Wird automatisch angemeldet und kann direkt arbeiten

Neue Benutzer erhalten die Rolle **Werkstatt** (kein Admin-Zugriff).

---

## Zusammenfassung für Tester

**Login:** `http://<DEINE-URL>/login`  
**Registrierung:** `http://<DEINE-URL>/register`  

**Admin-Zugang:** admin@warevision.local / admin123  
**Neue Benutzer:** Über /register Konto anlegen
