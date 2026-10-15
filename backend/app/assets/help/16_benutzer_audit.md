# Benutzer und Audit-Log (Administrator, Chef/Chefin)

## Benutzer anlegen
Benutzer → „+ Neuer Benutzer“: Vorname, Nachname, E-Mail (Login), Rolle und Passwort (mindestens 10 Zeichen). Bei „Bearbeiten“ bleibt ein leeres Passwortfeld unverändert. „Deaktivieren“ sperrt den Zugang, „Freischalten“ hebt die Sperre auf. Es muss immer mindestens eine aktive Person mit der Rolle Administrator oder Chef/Chefin geben.

## Rollen
Administrator und Chef/Chefin haben die gleichen Rechte: alles, dazu Benutzer, Rechte, Einstellungen und Audit-Log. Für Büro, Werkstatt und Mitarbeiter setzt die Rolle eine Vorlage, die du danach je Person ändern kannst:
- Büro: alle Bereiche sehen und ändern (Wartungspläne nur sehen), Sonderrecht „Rechnungen“.
- Werkstatt: Werkstattaufträge, Termine, Kunden, Fahrzeuge, Artikel, Lager, Inventur (zählen), Bestellungen (Wareneingang) und Dokumente ändern; Wartungspläne und Lieferanten sehen.
- Mitarbeiter: Termine und Werkstattaufträge ändern; Kunden, Fahrzeuge, Artikel, Lager, Wartungspläne und Dokumente nur sehen.

## Bereiche und Sonderrechte
Das Suchfeld filtert die Liste nach Name, E-Mail oder Rolle. Je Bereich legst du fest, ob die Person ihn sehen und ob sie ändern (anlegen, bearbeiten) darf. Sonderrechte schaltest du einzeln frei: „Rechnungen“, „Buchhaltung“, „DSGVO: Auskunft“ (Datenexport eines Kunden), „DSGVO: Löschen“ und „Lager & Einkauf“. Wer einen Bereich bearbeitet, darf Daten aus anderen Bereichen lesen, die er dafür auswählen muss (z. B. Kunden und Artikel im Werkstattauftrag), aber dort nichts ändern. Jede Änderung an Rolle und Rechten steht im Audit-Log.

## Zwei-Faktor-Anmeldung zurücksetzen
Die Spalte „2FA“ zeigt, wer die Zwei-Faktor-Anmeldung eingerichtet hat. Hat jemand ein neues Handy oder es verloren und keine Wiederherstellungscodes mehr, „2FA zurücksetzen“ klicken. Die Person richtet sie bei der nächsten Anmeldung neu ein. Das Zurücksetzen wird im Audit-Log protokolliert.

## Selbstregistrierung
Am PC können sich neue Benutzer über den Link /register selbst anlegen (auf dem Server ist das abgeschaltet); sie erhalten die Rolle „Werkstatt“. Das neue Konto ist zunächst gesperrt: Erst wenn Administrator oder Chef/Chefin unter Benutzer auf „Freischalten“ klicken, ist eine Anmeldung möglich.

## Audit-Log
Das Änderungsprotokoll zeigt, wer wann was geändert hat (z. B. Rechnung ausgestellt, Kunde geändert, Inventur abgeschlossen, Rechte eines Benutzers geändert). Filter nach Entität und Aktion; das Suchfeld durchsucht zusätzlich Benutzer (Name oder E-Mail) und die geänderten Werte (z. B. eine Rechnungsnummer). Einträge können nicht geändert werden.
