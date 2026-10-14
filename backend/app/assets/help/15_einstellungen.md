# Einstellungen (nur Admin)

## Firmendaten
Firmenname, Adresse, USt-IdNr., Logo (PNG/JPG/WebP, max. 2 MB), E-Mail, Telefon und Website erscheinen auf Rechnungen, Angeboten und PDFs. Die Adresse bitte so eintragen: Zeile 1 Straße und Hausnummer, Zeile 2 „PLZ Ort“ – das wird für die E-Rechnung ausgewertet.

## Bankverbindung
Kontoinhaber, Bank, IBAN und BIC erscheinen auf Rechnungen. Mit IBAN wird in der E-Rechnung „SEPA-Überweisung“ als Zahlungsart angegeben.

## Hinweis bei 0 % MwSt
Text, der auf Rechnungen mit 0-%-Positionen und in der E-Rechnung als Befreiungsgrund erscheint (z. B. für durchlaufende Posten). Den richtigen Wortlaut mit dem Steuerberater abstimmen.

## E-Mail-Versand
Entweder SMTP (Host, Port, Benutzer, Passwort, Absender) oder Resend (API-Key, Absender). „Test-E-Mail senden“ prüft die Einrichtung. Ohne E-Mail-Einrichtung sind die E-Mail-Buttons ohne Funktion.

## Stundenpreise
Stundenpreise (z. B. Mechaniker, Elektrik) mit Preis pro Stunde. Der als „Standard“ markierte wird im Auftrags- und Angebotsformular vorausgewählt.

## Terminmarktplatz
API-Schlüssel, Webhook-Basis-URL und Storno-Callback-URL für die automatische Terminübernahme von Terminmarktplatz.de.

## KI-Hilfe
API-Key für den KI-Assistenten der Hilfe (Anthropic/Claude) und optional das Modell. Ohne API-Key beantwortet die Hilfe Fragen mit einer Stichwortsuche in dieser Anleitung.

## System-Status und Hintergrundaufgaben
„Jetzt prüfen“ testet Datenbank und Redis. Hintergrundaufgaben: „Überfällige Rechnungen prüfen“ (täglich 08:00 Uhr) und „Wartungsintervalle prüfen“ (montags 07:00 Uhr); mit „Jetzt ausführen“ sofort starten. Ergebnisse stehen im Audit-Log.
