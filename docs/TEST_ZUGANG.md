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
