# Wartungspläne

## Wartungsplan anlegen
„+ Neuer Wartungsplan“: Hersteller und Name sind Pflicht, Modell optional (leer = gilt für alle Modelle des Herstellers). Intervalle in Kilometern, Betriebsstunden oder Monaten.

## Baujahr (z. B. ältere Fahrzeuge)
Mit „Baujahr von“ und „Baujahr bis“ gilt ein Plan nur für bestimmte Baujahre, z. B. ein eigener Plan „bis 2012“ für ältere Fahrzeuge und einer „ab 2013“ für neuere. Leer = alle Baujahre. Beim Werkstattauftrag wählt WareVision automatisch den passendsten Plan: zuerst Pläne für das Modell, dann Pläne für den Hersteller; jeweils hat ein Plan mit passendem Baujahr Vorrang vor einem Plan für alle Baujahre. Ist beim Fahrzeug kein Baujahr eingetragen, kommen nur Pläne ohne Baujahr in Frage. Die Spalte „Baujahre“ zeigt den Bereich.

## Aufgaben
Im Plan „+ Aufgabe hinzufügen“. Zu jeder Aufgabe kann ein benötigter Artikel mit Menge und Einheit verknüpft werden – dieser wird beim Anlegen eines Werkstattauftrags automatisch als Position übernommen.

## Hersteller-Dokument
Mit „+ Dokument hochladen (PDF)“ hinterlegst du das Wartungsheft des Herstellers; es kann im Auftrag geöffnet werden.

## Automatische Prüfung
Montags um 07:00 Uhr prüft WareVision alle aktiven Fahrzeuge auf überfällige Wartungsintervalle und schreibt Einträge ins Audit-Log.
