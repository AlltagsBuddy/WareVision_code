# Buchhaltung (nur Admin)

## Zeitraum und Übersicht
Zeitraum über die Schnellauswahl (z. B. Laufender Monat, Vormonat, Quartal, Jahr) oder Von/Bis wählen und „Rechnungen anzeigen“. Die Reiter zeigen Privatkunden (B2C), Händler (B2B) und Eingangsrechnungen.

## Eingangsrechnungen
Eingangsrechnungen sind Rechnungen, die die Werkstatt erhält (z. B. für Teile, Miete, Strom). „+ Neue Eingangsrechnung“ erfasst eine Papier- oder PDF-Rechnung von Hand (Lieferant, Nummer, Datum, Netto, MwSt, Kategorie). Bei einer Gutschrift des Lieferanten „Gutschrift des Lieferanten“ anhaken. „↑ PDF“ hängt den Beleg an. „Bezahlt“ markiert die Zahlung.

## E-Rechnung importieren
„↑ E-Rechnung importieren“ liest ZUGFeRD-PDFs und XRechnungen (XML, UBL oder CII) ein und legt automatisch eine Eingangsrechnung an. Das Original wird unverändert archiviert (Prüfsumme) und ist über „Original“ abrufbar. Importierte E-Rechnungen können nicht gelöscht werden; änderbar sind nur Status, Kategorie und Notizen. Dieselbe Rechnung kann nicht zweimal importiert werden. Eine normale PDF ohne eingebettete XML ist keine E-Rechnung und wird abgelehnt – dann manuell erfassen.

## Steuerberater-Export
„ZIP-Paket herunterladen“ erstellt für den gewählten Zeitraum ein Paket mit Ausgangsrechnungen (PDF, getrennt nach Privat/Händler), Eingangsrechnungen, CSV-Listen, einer USt-Zusammenfassung nach Monat, Typ und Steuersatz sowie einer LIESMICH-Datei.

## DATEV-Export
Der Bereich „DATEV-Export (Buchungsstapel)“ erzeugt Dateien im DATEV-Format, die dein Steuerberater direkt in DATEV einlesen kann. Das ZIP enthält: Buchungsstapel Ausgangsrechnungen (inkl. Stornorechnungen und Rechnungskorrekturen), Buchungsstapel Eingangsrechnungen, die Stammdaten der verwendeten Kunden- und Lieferantenkonten (Debitoren/Kreditoren) und eine LIESMICH-Datei. Entwürfe und stornierte Eingangsrechnungen werden nicht exportiert. Zahlungen sind nicht enthalten – die kommen beim Steuerberater über den Bankabruf.

## DATEV-Einstellungen
Vor dem ersten Export unter „DATEV-Einstellungen“ eintragen: Beraternummer und Mandantennummer (vom Steuerberater), Kontenrahmen (SKR03 oder SKR04), Sachkontenlänge (meist 4) und den Monat, in dem das Wirtschaftsjahr beginnt (meist Januar). Die Erlös- und Aufwandskonten je Steuersatz sind Vorschläge für den Kontenrahmen (SKR03: 8400/8300 Erlöse, 3400/3300 Wareneingang; SKR04: 4400/4300 und 5400/5300; 0 %: durchlaufende Posten) und sollten mit dem Steuerberater abgestimmt werden. Jeder Kunde bekommt beim ersten Export dauerhaft eine eigene Debitorennummer (ab 10000), jeder Lieferant eine Kreditorennummer (ab 70000); bereits vergebene Nummern ändern sich nie.

## DATEV: Vorschau und Hinweise
„Vorschau“ zeigt Anzahl der Belege und Buchungen, Summen und neue Konten, ohne etwas zu speichern. Belege, die nicht sicher automatisch gebucht werden können, stehen als Hinweis in der Vorschau und in der LIESMICH-Datei – z. B. ein nicht unterstützter Steuersatz oder eine Eingangsrechnung mit mehreren Steuersätzen. Diese bitte vom Steuerberater manuell buchen lassen. Ein Export darf nur ein Wirtschaftsjahr umfassen. Beim ersten Mal empfiehlt sich ein Probe-Import beim Steuerberater.

## Belegarchiv (GoBD)
Der Bereich „Belegarchiv (GoBD)“ zeigt, ob alle ausgegebenen Belege als unveränderbares Original gesichert sind: Rechnungen, Storno- und Korrekturbelege, Mahnbriefe sowie versendete Angebote und Bestellungen. Jedes Original ist mit einer Prüfsumme (SHA-256) gesichert und wird nie überschrieben. Belege von vor diesem Update haben noch kein Original: Einmalig „Fehlende Originale erzeugen“ klicken – am besten bevor Firmen- oder Kundendaten geändert werden; diese Originale sind als „nachträglich“ gekennzeichnet. „Archiv prüfen“ kontrolliert alle Archivdateien auf Vorhandensein und Veränderung. Meldet die Prüfung ein Problem, wird das Original nicht neu erzeugt – dann die Datei aus der Datensicherung zurückholen.
