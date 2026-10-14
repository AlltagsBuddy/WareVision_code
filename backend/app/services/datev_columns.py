"""Feldnamen des DATEV-Formats (EXTF), Stand Formatbeschreibung DATEV Dok.-Nr. 1003221 (09/2025).

Buchungsstapel: Formatkategorie 21, Formatversion 13, 125 Felder.
Debitoren/Kreditoren: Formatkategorie 16, Formatversion 5, 254 Felder.
DATEV liest die Felder nach ihrer Position; die Überschriften dienen der Lesbarkeit.
"""

BUCHUNGSSTAPEL_COLUMNS = [
    'Umsatz (ohne Soll/Haben-Kz)',  # 1
    'Soll/Haben-Kennzeichen',  # 2
    'WKZ Umsatz',  # 3
    'Kurs',  # 4
    'Basis-Umsatz',  # 5
    'WKZ Basis-Umsatz',  # 6
    'Konto',  # 7
    'Gegenkonto (ohne BU-Schlüssel)',  # 8
    'BU-Schlüssel',  # 9
    'Belegdatum',  # 10
    'Belegfeld 1',  # 11
    'Belegfeld 2',  # 12
    'Skonto',  # 13
    'Buchungstext',  # 14
    'Postensperre',  # 15
    'Diverse Adressnummer',  # 16
    'Geschäftspartnerbank',  # 17
    'Sachverhalt',  # 18
    'Zinssperre',  # 19
    'Beleglink',  # 20
    'Beleginfo - Art 1',  # 21
    'Beleginfo - Inhalt 1',  # 22
    'Beleginfo - Art 2',  # 23
    'Beleginfo - Inhalt 2',  # 24
    'Beleginfo - Art 3',  # 25
    'Beleginfo - Inhalt 3',  # 26
    'Beleginfo - Art 4',  # 27
    'Beleginfo - Inhalt 4',  # 28
    'Beleginfo - Art 5',  # 29
    'Beleginfo - Inhalt 5',  # 30
    'Beleginfo - Art 6',  # 31
    'Beleginfo - Inhalt 6',  # 32
    'Beleginfo - Art 7',  # 33
    'Beleginfo - Inhalt 7',  # 34
    'Beleginfo - Art 8',  # 35
    'Beleginfo - Inhalt 8',  # 36
    'KOST1 - Kostenstelle',  # 37
    'KOST2 - Kostenstelle',  # 38
    'KOST-Menge',  # 39
    'EU-Mitgliedstaat u. USt-IdNr.',  # 40
    'EU-Steuersatz',  # 41
    'Abw. Versteuerungsart',  # 42
    'Sachverhalt L+L',  # 43
    'Funktionsergänzung L+L',  # 44
    'BU 49 Hauptfunktionstyp',  # 45
    'BU 49 Hauptfunktionsnummer',  # 46
    'BU 49 Funktionsergänzung',  # 47
    'Zusatzinformation - Art 1',  # 48
    'Zusatzinformation - Inhalt 1',  # 49
    'Zusatzinformation - Art 2',  # 50
    'Zusatzinformation - Inhalt 2',  # 51
    'Zusatzinformation - Art 3',  # 52
    'Zusatzinformation - Inhalt 3',  # 53
    'Zusatzinformation - Art 4',  # 54
    'Zusatzinformation - Inhalt 4',  # 55
    'Zusatzinformation - Art 5',  # 56
    'Zusatzinformation - Inhalt 5',  # 57
    'Zusatzinformation - Art 6',  # 58
    'Zusatzinformation - Inhalt 6',  # 59
    'Zusatzinformation - Art 7',  # 60
    'Zusatzinformation - Inhalt 7',  # 61
    'Zusatzinformation - Art 8',  # 62
    'Zusatzinformation - Inhalt 8',  # 63
    'Zusatzinformation - Art 9',  # 64
    'Zusatzinformation - Inhalt 9',  # 65
    'Zusatzinformation - Art 10',  # 66
    'Zusatzinformation - Inhalt 10',  # 67
    'Zusatzinformation - Art 11',  # 68
    'Zusatzinformation - Inhalt 11',  # 69
    'Zusatzinformation - Art 12',  # 70
    'Zusatzinformation - Inhalt 12',  # 71
    'Zusatzinformation - Art 13',  # 72
    'Zusatzinformation - Inhalt 13',  # 73
    'Zusatzinformation - Art 14',  # 74
    'Zusatzinformation - Inhalt 14',  # 75
    'Zusatzinformation - Art 15',  # 76
    'Zusatzinformation - Inhalt 15',  # 77
    'Zusatzinformation - Art 16',  # 78
    'Zusatzinformation - Inhalt 16',  # 79
    'Zusatzinformation - Art 17',  # 80
    'Zusatzinformation - Inhalt 17',  # 81
    'Zusatzinformation - Art 18',  # 82
    'Zusatzinformation - Inhalt 18',  # 83
    'Zusatzinformation - Art 19',  # 84
    'Zusatzinformation - Inhalt 19',  # 85
    'Zusatzinformation - Art 20',  # 86
    'Zusatzinformation - Inhalt 20',  # 87
    'Stück',  # 88
    'Gewicht',  # 89
    'Zahlweise',  # 90
    'Forderungsart',  # 91
    'Veranlagungsjahr',  # 92
    'Zugeordnete Fälligkeit',  # 93
    'Skontotyp',  # 94
    'Auftragsnummer',  # 95
    'Buchungstyp',  # 96
    'USt-Schlüssel (Anzahlungen)',  # 97
    'EU-Mitgliedstaat (Anzahlungen)',  # 98
    'Sachverhalt L+L (Anzahlungen)',  # 99
    'EU-Steuersatz (Anzahlungen)',  # 100
    'Erlöskonto (Anzahlungen)',  # 101
    'Herkunft-Kz',  # 102
    'Leerfeld',  # 103
    'KOST-Datum',  # 104
    'SEPA-Mandatsreferenz',  # 105
    'Skontosperre',  # 106
    'Gesellschaftername',  # 107
    'Beteiligtennummer',  # 108
    'Identifikationsnummer',  # 109
    'Zeichnernummer',  # 110
    'Postensperre bis Datum',  # 111
    'Bezeichnung SoBil-Sachverhalt',  # 112
    'Kennzeichen SoBil-Buchung',  # 113
    'Festschreibung',  # 114
    'Leistungsdatum',  # 115
    'Datum Zuord. Steuerperiode',  # 116
    'Fälligkeit',  # 117
    'Generalumkehr (GU)',  # 118
    'Steuersatz',  # 119
    'Land',  # 120
    'Abrechnungsreferenz',  # 121
    'BVV-Position',  # 122
    'EU-Land u. USt-IdNr. (Ursprung)',  # 123
    'EU-Steuersatz (Ursprung)',  # 124
    'Abw. Skontokonto',  # 125
]

PERSONENKONTEN_COLUMNS = [
    'Konto',  # 1
    'Name (Adressatentyp Unternehmen)',  # 2
    'Unternehmensgegenstand',  # 3
    'Name (Adressatentyp natürl. Person)',  # 4
    'Vorname (Adressatentyp natürl. Person)',  # 5
    'Name (Adressatentyp keine Angabe)',  # 6
    'Adressatentyp',  # 7
    'Kurzbezeichnung',  # 8
    'EU-Land',  # 9
    'EU-USt-IdNr.',  # 10
    'Anrede',  # 11
    'Titel/Akad. Grad',  # 12
    'Adelstitel',  # 13
    'Namensvorsatz',  # 14
    'Adressart',  # 15
    'Straße',  # 16
    'Postfach',  # 17
    'Postleitzahl',  # 18
    'Ort',  # 19
    'Land',  # 20
    'Versandzusatz',  # 21
    'Adresszusatz',  # 22
    'Abweichende Anrede',  # 23
    'Abw. Zustellbezeichnung 1',  # 24
    'Abw. Zustellbezeichnung 2',  # 25
    'Kennz. Korrespondenzadresse',  # 26
    'Adresse gültig von',  # 27
    'Adresse gültig bis',  # 28
    'Telefon',  # 29
    'Bemerkung (Telefon)',  # 30
    'Telefon Geschäftsleitung',  # 31
    'Bemerkung (Telefon GL)',  # 32
    'E-Mail',  # 33
    'Bemerkung (E-Mail)',  # 34
    'Internet',  # 35
    'Bemerkung (Internet)',  # 36
    'Fax',  # 37
    'Bemerkung (Fax)',  # 38
    'Sonstige',  # 39
    'Bemerkung (Sonstige)',  # 40
    'Bankleitzahl 1',  # 41
    'Bankbezeichnung 1',  # 42
    'Bankkonto-Nummer 1',  # 43
    'Länderkennzeichen 1',  # 44
    'IBAN 1',  # 45
    'Leerfeld 1',  # 46
    'SWIFT-Code 1',  # 47
    'Abw. Kontoinhaber 1',  # 48
    'Kennz. Haupt-Bankverb. 1',  # 49
    'Bankverb. 1 Gültig von',  # 50
    'Bankverb. 1 Gültig bis',  # 51
    'Bankleitzahl 2',  # 52
    'Bankbezeichnung 2',  # 53
    'Bankkonto-Nummer 2',  # 54
    'Länderkennzeichen 2',  # 55
    'IBAN 2',  # 56
    'Leerfeld 2',  # 57
    'SWIFT-Code 2',  # 58
    'Abw. Kontoinhaber 2',  # 59
    'Kennz. Haupt-Bankverb. 2',  # 60
    'Bankverb. 2 gültig von',  # 61
    'Bankverb. 2 gültig bis',  # 62
    'Bankleitzahl 3',  # 63
    'Bankbezeichnung 3',  # 64
    'Bankkonto-Nummer 3',  # 65
    'Länderkennzeichen 3',  # 66
    'IBAN 3',  # 67
    'Leerfeld 3',  # 68
    'SWIFT-Code 3',  # 69
    'Abw. Kontoinhaber 3',  # 70
    'Kennz. Haupt-Bankverb. 3',  # 71
    'Bankverb. 3 gültig von',  # 72
    'Bankverb. 3 gültig bis',  # 73
    'Bankleitzahl 4',  # 74
    'Bankbezeichnung 4',  # 75
    'Bankkonto-Nummer 4',  # 76
    'Länderkennzeichen 4',  # 77
    'IBAN 4',  # 78
    'Leerfeld 4',  # 79
    'SWIFT-Code 4',  # 80
    'Abw. Kontoinhaber 4',  # 81
    'Kennz. Haupt-Bankverb. 4',  # 82
    'Bankverb. 4 Gültig von',  # 83
    'Bankverb. 4 Gültig bis',  # 84
    'Bankleitzahl 5',  # 85
    'Bankbezeichnung 5',  # 86
    'Bankkonto-Nummer 5',  # 87
    'Länderkennzeichen 5',  # 88
    'IBAN 5',  # 89
    'Leerfeld 5',  # 90
    'SWIFT-Code 5',  # 91
    'Abw. Kontoinhaber 5',  # 92
    'Kennz. Haupt-Bankverb. 5',  # 93
    'Bankverb. 5 gültig von',  # 94
    'Bankverb. 5 gültig bis',  # 95
    'Leerfeld 6',  # 96
    'Briefanrede',  # 97
    'Grußformel',  # 98
    'Kundennummer',  # 99
    'Steuernummer',  # 100
    'Sprache',  # 101
    'Ansprechpartner',  # 102
    'Vertreter',  # 103
    'Sachbearbeiter',  # 104
    'Diverse-Konto',  # 105
    'Ausgabeziel',  # 106
    'Währungssteuerung',  # 107
    'Kreditlimit (Debitor)',  # 108
    'Zahlungsbedingung',  # 109
    'Fälligkeit in Tagen (Debitor)',  # 110
    'Skonto in Prozent (Debitor)',  # 111
    'Kreditoren-Ziel 1 (Tage)',  # 112
    'Kreditoren-Skonto 1 (%)',  # 113
    'Kreditoren-Ziel 2 (Tage)',  # 114
    'Kreditoren-Skonto 2 (%)',  # 115
    'Kreditoren-Ziel 3 Brutto (Tage)',  # 116
    'Kreditoren-Ziel 4 (Tage)',  # 117
    'Kreditoren-Skonto 4 (%)',  # 118
    'Kreditoren-Ziel 5 (Tage)',  # 119
    'Kreditoren-Skonto 5 (%)',  # 120
    'Mahnung',  # 121
    'Kontoauszug',  # 122
    'Mahntext 1',  # 123
    'Mahntext 2',  # 124
    'Mahntext 3',  # 125
    'Kontoauszugstext',  # 126
    'Mahnlimit Betrag',  # 127
    'Mahnlimit %',  # 128
    'Zinsberechnung',  # 129
    'Mahnzinssatz 1',  # 130
    'Mahnzinssatz 2',  # 131
    'Mahnzinssatz 3',  # 132
    'Lastschrift',  # 133
    'Verfahren',  # 134
    'Mandantenbank',  # 135
    'Zahlungsträger',  # 136
    'Indiv. Feld 1',  # 137
    'Indiv. Feld 2',  # 138
    'Indiv. Feld 3',  # 139
    'Indiv. Feld 4',  # 140
    'Indiv. Feld 5',  # 141
    'Indiv. Feld 6',  # 142
    'Indiv. Feld 7',  # 143
    'Indiv. Feld 8',  # 144
    'Indiv. Feld 9',  # 145
    'Indiv. Feld 10',  # 146
    'Indiv. Feld 11',  # 147
    'Indiv. Feld 12',  # 148
    'Indiv. Feld 13',  # 149
    'Indiv. Feld 14',  # 150
    'Indiv. Feld 15',  # 151
    'Abweichende Anrede (Rechnungsadresse)',  # 152
    'Adressart (Rechnungsadresse)',  # 153
    'Straße (Rechnungsadresse)',  # 154
    'Postfach (Rechnungsadresse)',  # 155
    'Postleitzahl (Rechnungsadresse)',  # 156
    'Ort (Rechnungsadresse)',  # 157
    'Land (Rechnungsadresse)',  # 158
    'Versandzusatz (Rechnungsadresse)',  # 159
    'Adresszusatz (Rechnungsadresse)',  # 160
    'Abw. Zustellbezeichnung 1 (Rechnungsadresse)',  # 161
    'Abw. Zustellbezeichnung 2 (Rechnungsadresse)',  # 162
    'Adresse Gültig von (Rechnungsadresse)',  # 163
    'Adresse Gültig bis (Rechnungsadresse)',  # 164
    'Bankleitzahl 6',  # 165
    'Bankbezeichnung 6',  # 166
    'Bankkonto-Nummer 6',  # 167
    'Länderkennzeichen 6',  # 168
    'IBAN 6',  # 169
    'Leerfeld 7',  # 170
    'SWIFT-Code 6',  # 171
    'Abw. Kontoinhaber 6',  # 172
    'Kennz. Haupt-Bankverb. 6',  # 173
    'Bankverb 6 gültig von',  # 174
    'Bankverb 6 gültig bis',  # 175
    'Bankleitzahl 7',  # 176
    'Bankbezeichnung 7',  # 177
    'Bankkonto-Nummer 7',  # 178
    'Länderkennzeichen 7',  # 179
    'IBAN 7',  # 180
    'Leerfeld 8',  # 181
    'SWIFT-Code 7',  # 182
    'Abw. Kontoinhaber 7',  # 183
    'Kennz. Haupt-Bankverb. 7',  # 184
    'Bankverb 7 gültig von',  # 185
    'Bankverb 7 gültig bis',  # 186
    'Bankleitzahl 8',  # 187
    'Bankbezeichnung 8',  # 188
    'Bankkonto-Nummer 8',  # 189
    'Länderkennzeichen 8',  # 190
    'IBAN 8',  # 191
    'Leerfeld 9',  # 192
    'SWIFT-Code 8',  # 193
    'Abw. Kontoinhaber 8',  # 194
    'Kennz. Haupt-Bankverb. 8',  # 195
    'Bankverb 8 gültig von',  # 196
    'Bankverb 8 gültig bis',  # 197
    'Bankleitzahl 9',  # 198
    'Bankbezeichnung 9',  # 199
    'Bankkonto-Nummer 9',  # 200
    'Länderkennzeichen 9',  # 201
    'IBAN 9',  # 202
    'Leerfeld 10',  # 203
    'SWIFT-Code 9',  # 204
    'Abw. Kontoinhaber 9',  # 205
    'Kennz. Haupt-Bankverb. 9',  # 206
    'Bankverb 9 gültig von',  # 207
    'Bankverb 9 gültig bis',  # 208
    'Bankleitzahl 10',  # 209
    'Bankbezeichnung 10',  # 210
    'Bankkonto-Nummer 10',  # 211
    'Länderkennzeichen 10',  # 212
    'IBAN 10',  # 213
    'Leerfeld 11',  # 214
    'SWIFT-Code 10',  # 215
    'Abw. Kontoinhaber 10',  # 216
    'Kennz. Haupt-Bankverb. 10',  # 217
    'Bankverb 10 gültig von',  # 218
    'Bankverb 10 gültig bis',  # 219
    'Nummer Fremdsystem',  # 220
    'Insolvent',  # 221
    'SEPA-Mandatsreferenz 1',  # 222
    'SEPA-Mandatsreferenz 2',  # 223
    'SEPA-Mandatsreferenz 3',  # 224
    'SEPA-Mandatsreferenz 4',  # 225
    'SEPA-Mandatsreferenz 5',  # 226
    'SEPA-Mandatsreferenz 6',  # 227
    'SEPA-Mandatsreferenz 7',  # 228
    'SEPA-Mandatsreferenz 8',  # 229
    'SEPA-Mandatsreferenz 9',  # 230
    'SEPA-Mandatsreferenz 10',  # 231
    'Verknüpftes OPOS-Konto',  # 232
    'Mahnsperre bis',  # 233
    'Lastschriftsperre bis',  # 234
    'Zahlungssperre bis',  # 235
    'Gebührenberechnung',  # 236
    'Mahngebühr 1',  # 237
    'Mahngebühr 2',  # 238
    'Mahngebühr 3',  # 239
    'Pauschalberechnung',  # 240
    'Verzugspauschale 1',  # 241
    'Verzugspauschale 2',  # 242
    'Verzugspauschale 3',  # 243
    'Alternativer Suchname',  # 244
    'Status',  # 245
    'Anschrift manuell geändert (Korrespondenzadresse)',  # 246
    'Anschrift individuell (Korrespondenzadresse)',  # 247
    'Anschrift manuell geändert (Rechnungsadresse)',  # 248
    'Anschrift individuell (Rechnungsadresse)',  # 249
    'Fristberechnung bei Debitor',  # 250
    'Mahnfrist 1',  # 251
    'Mahnfrist 2',  # 252
    'Mahnfrist 3',  # 253
    'Letzte Frist',  # 254
]
