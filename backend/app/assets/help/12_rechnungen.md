# Rechnungen

## Rechnung erstellen (nur Admin)
„+ Neue Rechnung“: Quelle wählen – Werkstattauftrag (Positionen werden übernommen) oder manuell (Positionen eingeben). Kunde, Rechnungsdatum, Leistungsdatum, Fälligkeit und Anmerkungen angeben. Ohne Fälligkeit gilt Rechnungsdatum + 14 Tage. Eine neue Rechnung ist zunächst ein Entwurf.

## Leistungsdatum
Das Leistungsdatum ist der Tag, an dem die Leistung erbracht wurde (z. B. Reparatur fertig). Es ist eine Pflichtangabe auf Rechnungen (§ 14 Abs. 4 Nr. 6 UStG). Bleibt das Feld leer, wird das Rechnungsdatum verwendet.

## Ausstellen
„Ausstellen“ macht die Rechnung verbindlich. Danach ist sie unveränderbar (GoBD). Bei Rechnungen ohne Werkstattauftrag werden Artikelpositionen jetzt aus dem Lager gebucht.

## Versenden, PDF und E-Rechnung
„PDF“ bzw. „Vorschau“ zeigt die Rechnung. „E-Mail“ versendet sie (E-Mail-Versand muss in den Einstellungen eingerichtet sein). „ZUGFeRD“ lädt die E-Rechnung herunter: ein PDF mit eingebetteter XML-Datei nach EN 16931.

## Bezahlt, Erinnerung und Mahnung
„Als bezahlt“ markiert den Zahlungseingang. Überfällige Rechnungen sind rot markiert und über den Filter „Überfällig“ zu finden. Über die Mahnstufe (Erinnerung, 1. Mahnung, 2. Mahnung) wird die Stufe gesetzt; „Mahnbrief PDF“ erzeugt das Schreiben mit neuem Zahlungsziel.

## Stornieren
„Stornieren“ hebt eine Rechnung vollständig auf: Es entsteht eine Stornorechnung (Nummer STO-…) mit negativen Beträgen, die Originalrechnung wird als storniert markiert. Bei Rechnungen ohne Werkstattauftrag werden die Artikel ins Lager zurückgebucht. Der zugehörige Werkstattauftrag steht danach wieder auf „Abgeschlossen“ und kann neu abgerechnet werden. Wurde eine bezahlte Rechnung storniert, den Betrag an den Kunden zurücküberweisen. Gibt es zu einer Rechnung schon eine Rechnungskorrektur, ist Stornieren nicht mehr möglich – dann den Rest ebenfalls per Rechnungskorrektur gutschreiben.

## Gutschrift / Rechnungskorrektur (nur Admin)
Für Teilgutschriften bei ausgestellten oder bereits bezahlten Rechnungen, z. B. wenn ein Teil zurückgegeben wurde, zu viel berechnet wurde oder du Kulanz gewährst: In der Rechnungsliste „Gutschrift / Korrektur“ klicken. Je Position die gutzuschreibende Menge eintragen (höchstens die noch nicht gutgeschriebene Menge). Bei Lagerartikeln kannst du „zurück“ anhaken, dann wird die Menge wieder ins Lager gebucht (nur ganze Stück). Optional einen zusätzlichen Nachlass oder Kulanzbetrag (netto) mit einem Steuersatz der Rechnung eingeben. Der Grund ist Pflicht und steht auf dem Beleg. „Rechnungskorrektur erstellen“ erzeugt einen eigenen Beleg mit fortlaufender Nummer RK-… und negativen Beträgen. Er verweist auf Nummer und Datum der Originalrechnung; die Originalrechnung selbst bleibt unverändert (GoBD). Mehrere Korrekturen zu einer Rechnung sind möglich, insgesamt aber nicht mehr als der Rechnungsbetrag.

## Erstattung
Eine Rechnungskorrektur zeigt den Status „Erstattung offen“. War die Rechnung schon bezahlt, überweist du den Betrag an den Kunden zurück; war sie noch offen, zahlt der Kunde entsprechend weniger. Danach „Als erstattet“ klicken, der Status wird „Erstattet/verrechnet“. Rechnungskorrekturen und Stornorechnungen sind keine Forderungen: Sie werden nie als überfällig angezeigt und können nicht gemahnt werden. PDF, E-Mail und ZUGFeRD funktionieren wie bei Rechnungen. Eine falsche Rechnungskorrektur kann storniert werden; zurückgebuchte Teile werden dabei wieder aus dem Lager gebucht.

## MwSt und Pflichtangaben
Die MwSt wird je Steuersatz ausgewiesen und gerundet (z. B. 19 % und 7 % getrennt). Bei Positionen mit 0 % erscheint der Hinweistext aus den Einstellungen. Firmendaten, USt-IdNr. und Bankverbindung kommen aus den Einstellungen.

## ZUGFeRD importieren (Anzeige)
„ZUGFeRD importieren“ zeigt die Daten einer ZUGFeRD-PDF nur an. Zum Speichern von Lieferantenrechnungen Buchhaltung → Eingangsrechnungen → „E-Rechnung importieren“ verwenden.
