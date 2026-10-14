# Werkstattaufträge

## Auftrag anlegen
„+ Neuer Auftrag“: Kunde und Fahrzeug sind Pflicht (Fahrzeugsuche nach Kennzeichen oder FIN). Optional: Marke/Modell, Wartungsplan, Termin (vorhandenen wählen oder neuen anlegen), Kundenbeschwerde/Anliegen, interne Notizen, Kilometerstand bei Abgabe und geschätzte Arbeitszeit.
- Wartungsplan: Ist für Fahrzeug/Modell ein Plan vorhanden, wird er automatisch gewählt. Pläne mit passendem Baujahr-Bereich haben Vorrang (siehe Wartungspläne). Artikel aus den Plan-Aufgaben werden als Positionen übernommen.
- Stundenpreis + geschätzte Arbeitszeit: Es wird automatisch ein Arbeitszeit-Posten angelegt.
Aufträge können auch aus einem Angebot entstehen („In Werkstattauftrag umwandeln“).

## Positionen
Im Auftrag „+ Position hinzufügen“: Typ Arbeit, Teile oder Service. Bei Arbeit kann ein Stundensatz gewählt werden, bei Teilen ein Artikel (Preis wird übernommen). Teile mit Artikel werden sofort aus dem Lager gebucht; beim Entfernen der Position wird zurückgebucht. Lagerartikel nur in ganzen Stück.

## Status
Neu → Geplant → In Arbeit → Abgeschlossen → Abgerechnet (oder Storniert). Den Status änderst du im Auftrag über die Auswahl „Status“. „Abgerechnet“ wird automatisch gesetzt, wenn eine Rechnung erstellt wird. In abgerechneten oder stornierten Aufträgen können keine Positionen mehr hinzugefügt werden.

## Drucken und abrechnen
„Auftrag drucken / Vorschau“ erzeugt ein PDF als Abhakliste für die Werkstatt. „Rechnung erstellen“ öffnet die Rechnungen mit dem Auftrag vorausgewählt; alle Positionen werden übernommen. Wird die Rechnung storniert, steht der Auftrag wieder auf „Abgeschlossen“: Du kannst Positionen entfernen oder hinzufügen (entfernte Teile werden ins Lager zurückgebucht) und danach mit „Rechnung erstellen“ eine neue Rechnung mit neuer Nummer anlegen. Die stornierte Rechnung und die Stornorechnung bleiben unverändert erhalten.

## Fotos
Im Auftrag unter „Fotos“: „Foto aufnehmen“ öffnet die Kamera direkt im Programm – am Notebook die Webcam, an Tablet oder Smartphone die Rückkamera (bei mehreren Kameras ist eine Auswahl möglich). Beim ersten Mal fragt der Browser, ob die Kamera benutzt werden darf: „Zulassen“ wählen. Mit „Auslösen“ wird das Foto gespeichert. Die Kamera im Programm funktioniert nur über https oder direkt am Rechner (localhost); wird WareVision am Handy über http und die IP-Adresse geöffnet, öffnet „Foto aufnehmen“ stattdessen die Kamera-App des Handys. „Bilder auswählen“ lädt eines oder mehrere vorhandene Bilder hoch (JPEG, PNG oder WebP, max. 15 MB je Foto, max. 30 Fotos je Auftrag). iPhone-Fotos im HEIC-Format bitte als JPEG aufnehmen (iPhone: Einstellungen → Kamera → Formate → „Maximale Kompatibilität“). Foto anklicken zum Vergrößern, Beschreibung eintragen (z. B. „Kratzer links vorne“) oder Foto entfernen. Hinzufügen und Entfernen wird im Audit-Log protokolliert. Fotos erscheinen nur im Programm, nicht auf dem gedruckten Auftrag. Wird ein Kunde nach DSGVO anonymisiert, werden die Fotos seiner Aufträge gelöscht, da sie oft Kennzeichen oder FIN zeigen.
