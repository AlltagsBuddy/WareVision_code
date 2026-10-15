# Artikel, Lagerorte und Kategorien

## Artikel anlegen
„+ Neuer Artikel“: Pflicht sind Artikelnummer und Bezeichnung. Außerdem: Barcode (EAN/GTIN), Kategorie, Lieferant, Lagerort, Beschreibung, Einkaufspreis (EK), Verkaufspreise B2C und B2B, MwSt-Satz, Mindestbestand, Zielbestand, Artikelnummer beim Lieferanten, Hersteller des Teils (Marke, z. B. NGK oder Original-Teil) und die Fahrzeugmodelle, zu denen der Artikel passt.

## Barcode und Kamera
Im Feld „Barcode (Enter)“ kannst du mit einem Handscanner scannen. Mit „Kamera scannen“ nutzt du die Kamera (Notebook-Webcam, Tablet oder Smartphone): Barcode vor die Kamera halten, er wird automatisch erkannt. Klappt das nicht, „Foto aufnehmen“ klicken – dann wird das aktuelle Kamerabild nach dem Code durchsucht. „Bild auswählen“ liest den Code aus einem vorhandenen Foto. Die Kamera im Browser funktioniert nur über https oder direkt am Rechner (localhost).

## Unbekannten Barcode zuordnen
Gehört ein gescannter Barcode noch zu keinem Artikel, erscheint „ist noch keinem Artikel zugeordnet“. Dann entweder im Feld darunter den vorhandenen Artikel suchen und „Zuordnen“ klicken, oder „+ Neuer Artikel mit diesem Barcode“ wählen. Ab dann wird der Artikel beim Scannen erkannt. Im Artikel-Formular füllt „Scannen“ neben dem Barcode-Feld den Code per Kamera ein. Ein Barcode kann nur zu einem Artikel gehören; hat der Artikel schon einen anderen Barcode, fragt WareVision vor dem Ersetzen nach. Die Zuordnung steht im Audit-Log.

## Lagerorte und Kategorien verwalten
Über die Buttons „Lagerorte“ und „Kategorien“ legst du diese an, benennst sie um oder löschst sie. Lagerorte helfen bei der Inventur (Teilinventur je Lagerort).

## Bestand
Der Bestand eines Artikels wird nicht direkt bearbeitet, sondern über Lagerbewegungen (Bereich Lager), Werkstattaufträge, Rechnungen und Inventur geändert. So bleibt jede Änderung nachvollziehbar.

## Mindestbestand
Fällt der Bestand unter den Mindestbestand, erscheint der Artikel im Lager unter „Mindestbestand (Warnung)“, auf dem Dashboard und im Bestellvorschlag (Bestellungen). Der Zielbestand legt fest, bis zu welcher Menge nachbestellt wird (z. B. Mindestbestand 2, Zielbestand 6). Ohne Zielbestand wird bis zum Mindestbestand aufgefüllt. Die „Artikelnummer beim Lieferanten“ erscheint auf der Bestellung.

## Suchen und passende Teile
Das Suchfeld findet Artikel nach Artikelnummer, Bezeichnung, OEM-Nummer, Lieferanten-Artikelnummer und Hersteller des Teils. Mit „Alle Fahrzeugmodelle“ zeigst du nur die Artikel, die zu einem bestimmten Modell passen. Unter Fahrzeuge führt „Passende Teile“ direkt zu dieser Liste für das Modell des Fahrzeugs. Die Spalten zeigen EK, Hersteller und die passenden Modelle.
