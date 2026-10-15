# WareVision auf dem Server (Hetzner) – Schritt für Schritt

Ziel: WareVision läuft auf dem Server und ist vom Handy, Tablet und PC **überall** über
`https://…` erreichbar – auch wenn der PC aus ist. Anmeldung mit Passwort **und**
Zwei-Faktor-Code (Pflicht auf dem Server).

**Ein Kunde = eine eigene Instanz:** eigene Adresse (z. B. `quadparadies.warevision.de`),
eigene Datenbank, eigene Dateien. So sind die Daten der Kunden sauber getrennt.

> Platzhalter in `<spitzen Klammern>` durch eure Werte ersetzen.
> Befehle für den Server (Linux) laufen in einer SSH-Sitzung, Befehle für den PC in PowerShell.

---

## 0. Vorher klären (einmalig)

1. **Domain:** Die Domain (z. B. `warevision.de`) muss dir gehören, damit du beim Domain-Anbieter
   einen DNS-Eintrag setzen kannst.
2. **Rechtliches (Datenschutz):** Auf dem Server verarbeitest du (AlltagsBuddy) Kundendaten von
   Quadparadies Schonath. Dafür braucht es einen **Vertrag zur Auftragsverarbeitung (AVV) nach
   Art. 28 DSGVO** zwischen Quadparadies Schonath (Verantwortlicher) und AlltagsBuddy
   (Auftragsverarbeiter) – und mit Hetzner (im Hetzner-Konto unter „Auftragsverarbeitung“
   abschließbar). Die Verfahrensdokumentation (Abschnitt 3.1 Hard-/Software, 3.5 Zugriffsschutz,
   4.1 Datensicherung) ist anzupassen. *Ich bin kein Anwalt – den AVV bitte prüfen lassen.*
3. **Standardpasswort:** Hat ein Konto noch `admin123`, ist es auf dem Server gesperrt.
   Am besten vor dem Umzug am PC ändern (rechts oben → Passwort ändern, mind. 10 Zeichen).

## 1. Server prüfen

Per SSH auf dem Server anmelden und nachsehen, ob Docker installiert ist und wer Port 80/443 belegt:

```bash
docker --version
docker compose version
sudo ss -ltnp | grep -E ':(80|443) '
docker ps --format '{{.Names}}\t{{.Ports}}'
```

- Keine Ausgabe bei `ss` → **Variante A** (WareVision bringt seinen eigenen Webserver Caddy mit).
- Es läuft schon ein Webserver (nginx, Caddy, Traefik – z. B. für Terminmarktplatz) → **Variante B**.
- Unsicher? Die Ausgabe an Claude schicken.

## 2. DNS-Eintrag setzen

Beim Domain-Anbieter einen **A-Eintrag** anlegen:

| Name | Typ | Wert |
|---|---|---|
| `quadparadies` (bei Domain `warevision.de`) | A | `<IPv4 des Servers>` |

Hat der Server auch IPv6, zusätzlich einen **AAAA-Eintrag** mit der IPv6-Adresse.
Prüfen (nach einigen Minuten): `ping quadparadies.warevision.de` zeigt die Server-IP.

## 3. Programm auf den Server holen

```bash
sudo mkdir -p /opt/warevision && sudo chown $USER /opt/warevision
cd /opt/warevision
git clone https://github.com/AlltagsBuddy/WareVision_code.git quadparadies
cd quadparadies
```
(Das Repository ist privat: Git fragt nach deinem GitHub-Zugang – Benutzername und ein
persönliches Zugriffstoken. Das gibst du selbst ein.)

## 4. Einstellungen (.env) anlegen

```bash
cp infra/server/env.example .env
openssl rand -hex 32     # Ausgabe als SECRET_KEY eintragen
openssl rand -hex 32     # zweite Ausgabe als POSTGRES_PASSWORD eintragen
nano .env
chmod 600 .env
```

In `.env` eintragen: `WAREVISION_DOMAIN=quadparadies.warevision.de`, `SECRET_KEY`, `POSTGRES_PASSWORD`.
Läuft schon eine andere Anwendung auf Port 8080, `HTTP_PORT` ändern (z. B. 8081).

> **SECRET_KEY nie ändern**, wenn WareVision einmal läuft – sonst sind alle Anmeldungen und die
> Zwei-Faktor-Einrichtungen ungültig (dann müsste jede Person 2FA neu einrichten).
> Die `.env` gehört in die Datensicherung (z. B. Passwort-Manager), nicht in Git.

Zur Abkürzung für alle weiteren Befehle (in jeder neuen SSH-Sitzung einmal eingeben):

```bash
cd /opt/warevision/quadparadies
alias wv='docker compose -p quadparadies -f docker-compose.prod.yml --env-file .env'
```

## 5. Starten

**Variante A – Port 80/443 sind frei (eingebauter Webserver Caddy):**
```bash
wv --profile caddy up -d --build
```
Caddy holt das https-Zertifikat automatisch (Let's Encrypt). Port 80 und 443 müssen in der
Hetzner-Firewall offen sein.

**Variante B – es läuft schon ein Webserver:**
```bash
wv up -d --build
```
WareVision lauscht dann nur lokal auf `127.0.0.1:8080`. Im vorhandenen Webserver eine Weiterleitung
für die Domain eintragen – Vorlagen: `infra/server/nginx-beispiel.conf` (nginx + certbot) bzw.
`infra/server/caddy-beispiel.txt` (Caddy).

**Prüfen:**
```bash
wv ps                      # alle Dienste „running“ bzw. „healthy“
wv logs --tail=50 backend  # muss mit „Application startup complete“ enden
```
Dann im Browser `https://quadparadies.warevision.de` öffnen – es erscheint die Anmeldung.

Startet das Backend nicht und meldet „unsichere Einstellungen“: `.env` prüfen
(SECRET_KEY mind. 32 Zeichen, eigenes POSTGRES_PASSWORD, WAREVISION_DOMAIN gesetzt).

## 6. Daten vom PC übernehmen

> Ab dem Umzug nur noch auf dem Server arbeiten. Sonst entstehen zwei unterschiedliche Datenstände
> (und doppelte Rechnungsnummern).

**Am PC (PowerShell), WareVision läuft noch:**
```powershell
cd D:\WareVision\WareVision_code
mkdir D:\WareVision\umzug
docker compose exec postgres pg_dump -U warevision -Fc -f /tmp/umzug.dump warevision
docker compose cp postgres:/tmp/umzug.dump D:\WareVision\umzug\warevision.dump
docker compose exec backend tar -czf /tmp/dateien.tar.gz -C /app/uploads .
docker compose cp backend:/tmp/dateien.tar.gz D:\WareVision\umzug\dateien.tar.gz
docker compose stop
```
Danach liegen in `D:\WareVision\umzug` zwei Dateien: `warevision.dump` (Datenbank) und
`dateien.tar.gz` (Belegarchiv, E-Rechnungen, Dokumente, Fotos).

**Auf den Server kopieren (PowerShell):**
```powershell
scp D:\WareVision\umzug\warevision.dump D:\WareVision\umzug\dateien.tar.gz <benutzer>@<server-ip>:/opt/warevision/quadparadies/
```

**Auf dem Server einspielen:**
```bash
cd /opt/warevision/quadparadies
alias wv='docker compose -p quadparadies -f docker-compose.prod.yml --env-file .env'
wv stop backend celery-worker celery-beat
wv cp warevision.dump postgres:/tmp/warevision.dump
wv exec postgres pg_restore -U warevision -d warevision --clean --if-exists --no-owner /tmp/warevision.dump
wv run --rm --no-deps -v "$PWD:/umzug" backend sh -c "tar -xzf /umzug/dateien.tar.gz -C /app/uploads"
wv up -d
wv logs --tail=30 backend    # zeigt „Vorhandene Datenbank: Migrationen werden ausgeführt“
```

**Prüfen:** In WareVision anmelden → Buchhaltung → „Archiv prüfen“ muss „vollständig und
unverändert“ melden. Stichprobe: eine alte Rechnung als PDF öffnen.

**Aufräumen (Datenschutz):** Die Umzugsdateien enthalten alle Kundendaten.
```bash
rm /opt/warevision/quadparadies/warevision.dump /opt/warevision/quadparadies/dateien.tar.gz
```
und am PC den Ordner `D:\WareVision\umzug` löschen (Papierkorb leeren).

## 7. Erste Anmeldung und Zwei-Faktor

Jede Person meldet sich einmal an und richtet die Zwei-Faktor-Anmeldung ein (QR-Code mit
Google Authenticator oder Microsoft Authenticator scannen, Code eingeben, Wiederherstellungscodes
sichern). Details: Hilfe → Erste Schritte.

**Notfälle (auf dem Server):**
```bash
wv exec backend python scripts/manage_user.py list
wv exec backend python scripts/manage_user.py set-password <email>   # Passwort neu setzen
wv exec backend python scripts/manage_user.py reset-2fa <email>      # 2FA neu einrichten lassen
```

**Neue, leere Installation ohne PC-Daten:** vor dem Start `ADMIN_EMAIL` und `ADMIN_PASSWORD`
(mind. 10 Zeichen) in `.env` setzen; nach der ersten Anmeldung beide Werte wieder leeren.

## 8. Weitere Einstellungen anpassen

- **Terminmarktplatz:** Die Webhook-Adresse ändert sich auf
  `https://quadparadies.warevision.de/api/v1/appointments/webhook/termin-marktplatz` –
  bei Terminmarktplatz eintragen.
- **E-Mail-Versand** (SMTP/Resend) und Firmendaten kommen mit der Datenbank mit; einmal eine
  Test-E-Mail senden.

## 9. Tägliche Datensicherung auf dem Server

```bash
wv --profile backup run --rm backup     # einmal testen: legt 2 Dateien in ./backups an
ls -la backups
crontab -e
```
In der Crontab diese Zeile ergänzen (täglich 2:15 Uhr):
```
15 2 * * * cd /opt/warevision/quadparadies && docker compose -p quadparadies -f docker-compose.prod.yml --env-file .env --profile backup run --rm backup >> backups/backup.log 2>&1
```
**Außer Haus sichern:** Die Dateien in `backups/` zusätzlich regelmäßig an einen zweiten Ort
kopieren (z. B. Hetzner Storage Box oder verschlüsselt auf eine externe Festplatte).
Eine Sicherung nur auf demselben Server schützt nicht vor Serverausfall.
Mindestens einmal im Jahr eine Wiederherstellung testen (wie Schritt 6) und in der
Verfahrensdokumentation eintragen.

## 10. Updates einspielen

```bash
cd /opt/warevision/quadparadies
wv --profile backup run --rm backup     # vorher sichern
git pull
wv up -d --build                         # Variante A zusätzlich: --profile caddy
wv logs --tail=30 backend
```
Datenbank-Änderungen (Migrationen) laufen beim Start automatisch.

## 11. Weiterer Kunde

Für jeden Kunden einen eigenen Ordner, eigene `.env`, eigenen Projektnamen und eigene Subdomain:
```bash
cd /opt/warevision
git clone https://github.com/AlltagsBuddy/WareVision_code.git <kunde>
cd <kunde> && cp infra/server/env.example .env   # neue Zufallswerte, andere Domain, anderer HTTP_PORT
docker compose -p <kunde> -f docker-compose.prod.yml --env-file .env up -d --build
```
Mit eingebautem Caddy (Variante A) kann nur **eine** Instanz Port 80/443 belegen. Ab dem zweiten
Kunden deshalb Variante B nutzen (ein Webserver leitet alle Subdomains weiter).

## Was auf dem Server anders ist als am PC

| Thema | PC | Server |
|---|---|---|
| Zugriff | nur im eigenen Netz | überall über https |
| Zwei-Faktor | freiwillig | Pflicht für alle |
| Standardpasswort `admin123` | erlaubt | gesperrt |
| Selbstregistrierung (/register) | an | aus (Admin legt Benutzer an) |
| API-Dokumentation (/docs) | an | aus |
| Datenbank/Redis von außen | Ports offen | nicht erreichbar |
| Kamera im Browser | nur am PC selbst | auf allen Geräten (https) |
