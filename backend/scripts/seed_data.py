"""Seed demo data: Lieferanten, Fahrzeuge, Werkstattaufträge, Rechnungen, Dokumente (je 50)."""

import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.article import Article
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.customer import Customer, CustomerAddress
from app.models.document import Document
from app.models.invoice import Invoice, InvoiceItem
from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
from app.models.manufacturer import Manufacturer, VehicleModel
from app.models.supplier import Supplier
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem

# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

ADDRESSES = [
    ("Hauptstraße", "12", "80331", "München"),
    ("Berliner Platz", "5a", "90402", "Nürnberg"),
    ("Am Markt", "8", "70173", "Stuttgart"),
    ("Königstraße", "22", "70173", "Stuttgart"),
    ("Marienplatz", "1", "80331", "München"),
    ("Bahnhofstraße", "45", "60311", "Frankfurt"),
    ("Schillerstraße", "3", "10117", "Berlin"),
    ("Goethestraße", "17", "50667", "Köln"),
    ("Industriestraße", "100", "40213", "Düsseldorf"),
    ("Lindenweg", "7", "86150", "Augsburg"),
    ("Bergstraße", "33", "69115", "Heidelberg"),
    ("Rosenweg", "2", "90408", "Nürnberg"),
    ("Gewerbegebiet Nord", "15", "93053", "Regensburg"),
    ("Werkstraße", "88", "71063", "Sindelfingen"),
    ("Musterstraße", "42", "20095", "Hamburg"),
    ("Feldweg", "5", "04103", "Leipzig"),
    ("Talstraße", "9", "01067", "Dresden"),
    ("Parkstraße", "21", "50825", "Köln"),
    ("Ringstraße", "66", "01099", "Dresden"),
    ("Sonnenallee", "3", "12045", "Berlin"),
]

MANUFACTURERS = [
    "Yamaha", "Honda", "Kawasaki", "Suzuki", "KTM", "CFMOTO", "Polaris",
    "Can-Am", "Arctic Cat", "Husqvarna Motorcycles", "BMW Motorrad",
    "Ducati", "Triumph", "Aprilia", "Beta", "Sherco", "GasGas",
    "Benelli", "Royal Enfield", "Indian", "Harley-Davidson",
    "Husaberg", "TM Racing", "Fantic", "Rieju",
]

MODELS = {
    "Yamaha":       ["Grizzly 700", "Kodiak 450", "Raptor 700", "YFZ450", "Wolverine"],
    "Honda":        ["Foreman", "Rancher", "Pioneer", "Talon", "TRX420"],
    "Kawasaki":     ["Brute Force", "Mule", "Teryx", "KFX", "KLR650"],
    "Suzuki":       ["King Quad", "QuadSport", "DR650", "V-Strom", "GSX-R"],
    "KTM":          ["XCF", "EXC", "SX-F", "Freeride", "1290 Super Duke"],
    "CFMOTO":       ["CForce 450", "ZForce 800", "UForce 1000", "CForce 625", "ZForce 550"],
    "Polaris":      ["Sportsman 570", "Ranger 1000", "RZR Pro R", "Scrambler 850", "General 1000"],
    "Can-Am":       ["Outlander 650", "Renegade 1000R", "Maverick X3", "Defender HD10", "Commander XT"],
    "BMW Motorrad": ["R1250GS", "S1000RR", "F850GS", "R18", "M1000RR"],
    "Ducati":       ["Panigale V4", "Monster SP", "Scrambler Icon", "Multistrada V4"],
    "Triumph":      ["Tiger 900", "Bonneville T120", "Speed Triple", "Scrambler 1200"],
    "Aprilia":      ["RSV4", "Tuono V4", "RS 660", "Shiver 900"],
}

ARTICLES = [
    # (art_nr, name, ek, vk_b2c, min_stock, barcode,             oem,          beschreibung)
    ("ART-001", "Motoröl 10W-40 4L",              24.90,  34.90,  10, "4006501346221", "MO-10W40-4L",  "Vollsynthetisches Motoröl, für 4-Takt-Motoren"),
    ("ART-002", "Ölfilter Standard",               4.50,   9.90,   5, "4006501111234", "OF-STANDARD",  "Passend für gängige Quad- und Motorradmotoren"),
    ("ART-003", "Luftfilter trocken",              8.90,  18.90,   5, "4006501222345", "LF-TROCKEN",   "Hochleistungs-Trockenluftfilter"),
    ("ART-004", "Bremsscheibe vorn",              45.00,  89.00,   3, "4008767188996", "BS-VORN-250",  "Ø 250mm, gelocht und geschlitzt"),
    ("ART-005", "Bremsbeläge Satz",               28.00,  55.00,   5, "4005010900664", "BB-SATZ-SIN",  "Sinterbelag, vorn und hinten verwendbar"),
    ("ART-006", "Zündkerze NGK CR8E",              3.50,   7.90,  10, "4047972173559", "ZK-NGK-CR8E",  "Standardzündkerze für Quad und Motorrad"),
    ("ART-007", "Keilriemen CVT",                 18.00,  38.00,   3, "4011905123456", "KR-CVT-800",   "CVT-Antriebsriemen 800x22mm"),
    ("ART-008", "Kupplungsbelag Satz",            65.00, 125.00,   2, "4011905234567", "KB-SATZ-6T",   "6-teiliger Satz, organisch"),
    ("ART-009", "Getriebeöl 1L",                  12.00,  22.00,   5, "4006501455678", "GO-75W90-1L",  "75W-90 Getriebeöl vollsynthetisch"),
    ("ART-010", "Kühlmittel G12+ 5L",             18.00,  32.00,   5, "4006501566789", "KM-G12-5L",    "Kühlmittel rosarot, fertig gemischt -35°C"),
    ("ART-011", "Bremsflüssigkeit DOT4",           6.50,  12.90,   5, "4005010900665", "BF-DOT4-500",  "DOT 4, 500ml Flasche"),
    ("ART-012", "Fett Kardanwellen",               8.00,  15.00,   3, None,            "FT-KARDAN",    "Hochdruckfett für Gelenkwellen"),
    ("ART-013", "Luftfilter Ölbad",               22.00,  45.00,   3, "4006501677890", "LF-OELBAD",    "Ölbad-Luftfilter, universell 38-44mm"),
    ("ART-014", "Starterbatterie 12V 14Ah",       45.00,  89.00,   2, "4047972288901", "SB-12V-14AH",  "Wartungsfreie Bleibatterie YTX14-BS"),
    ("ART-015", "Reifen vorn 25x8-12",            55.00, 110.00,   2, None,            "RF-25X8-12",   "ATV-Reifen vorne, 6-lagig"),
    ("ART-016", "Reifen hinten 25x10-12",         65.00, 130.00,   2, None,            "RF-25X10-12",  "ATV-Reifen hinten, 6-lagig"),
    ("ART-017", "Schlauch 4.00-8",                12.00,  24.00,   3, "4006501799012", "SL-400-8",     "Innenluftschlauch für Geländereifen"),
    ("ART-018", "Bremsflüssigkeit DOT5.1",         9.00,  18.00,   3, "4005010900666", "BF-DOT51-500", "DOT 5.1 Hochleistungsbremsflüssigkeit"),
    ("ART-019", "Kettensatz komplett",             85.00, 165.00,   2, "4047972300123", "KS-520-110",   "520er Kette 110 Glieder + Ritzel + Kettenrad"),
    ("ART-020", "Kettenöl Spray 400ml",            8.50,  16.90,  10, "4011905311234", "KO-SPRAY-400", "Haftkettenöl, weiß, Spray 400ml"),
    ("ART-021", "Schaltöl 75W-90 1L",             14.00,  26.00,   5, "4006501322345", "SO-75W90-1L",  "Schaltgetriebeöl für Handschaltgetriebe"),
    ("ART-022", "Lenkkopflager Satz",             35.00,  69.00,   2, "4047972433456", "LK-SATZ-TRX",  "Oberes und unteres Lenkkopflager"),
    ("ART-023", "Radlager vorn",                  28.00,  54.00,   3, "4047972444567", "RL-VORN-6205", "Radlager 25x52x15, innen und außen"),
    ("ART-024", "Stoßdämpfer vorn",              110.00, 215.00,   1, None,            "SD-VORN-350",  "Gabelholm vorn, komplett überholt"),
    ("ART-025", "Stoßdämpfer hinten",            125.00, 245.00,   1, None,            "SD-HINT-400",  "Hinterrad-Stoßdämpfer mit Feder"),
    ("ART-026", "Dichtung Zylinderkopf",          22.00,  45.00,   3, "4005204027990", "DI-ZK-450",    "Zylinderkopfdichtung, Kupfer/Stahl"),
    ("ART-027", "Kolben Ø 96mm",                  58.00, 112.00,   1, None,            "KO-96MM-STD",  "Schmiedekolben Standardmaß, inkl. Ringe"),
    ("ART-028", "Bremshebel vorn",                15.00,  32.00,   3, "4001171054363", "BH-VORN-EINST","Einstellbarer Aluminium-Bremshebel"),
    ("ART-029", "Kupplungshebel",                 15.00,  32.00,   3, "4001171054364", "BH-KUPP-EINST","Einstellbarer Aluminium-Kupplungshebel"),
    ("ART-030", "Fußrasten Satz",                 45.00,  95.00,   2, None,            "FR-SATZ-ALU",  "CNC-gefräste Aluminium-Fußrasten, 4-teilig"),
    ("ART-031", "Bremsscheibe hinten",            38.00,  75.00,   3, "4008767299001", "BS-HINT-220",  "Ø 220mm, Wave-Design"),
    ("ART-032", "Lenkungsdämpfer",                85.00, 165.00,   1, None,            "LD-HYDRO-ADJ", "Hydraulischer Lenkungsdämpfer, einstellbar"),
    ("ART-033", "Lichtmaschine Regler",           28.00,  55.00,   2, "4047972500112", "LM-REGLER-12V","Spannungsregler 12V, 35A"),
    ("ART-034", "Zündspule",                      35.00,  68.00,   2, "4047972511223", "ZS-CDI-6PIN",  "Zündspule für CDI-Systeme, 6-polig"),
    ("ART-035", "Vergaser 30mm",                  55.00, 108.00,   1, None,            "VG-30MM-KEIHIN","Keihin-Vergaser 30mm Schieber"),
    ("ART-036", "Kraftstofffilter",                4.90,   9.90,  10, "4006501633334", "KF-INLINE-6MM","Inline-Kraftstofffilter 6mm Anschluss"),
    ("ART-037", "Handschutz Paar",                22.00,  44.00,   3, None,            "HS-PAAR-22MM", "Lenkerhandschutz, Aluminium 22mm"),
    ("ART-038", "Sturzpad Satz",                  18.00,  38.00,   3, None,            "SP-SATZ-NYLON","Nylon-Sturzpads, selbstklebend, 6 Stück"),
    ("ART-039", "Ventildeckeldichtung",            8.00,  16.00,   5, "4005204038991", "VD-DICHT-GUMMI","Gummidichtung Ventildeckel"),
    ("ART-040", "Simmerring Kurbelwelle",          6.50,  13.00,   5, "4047972622334", "SR-KW-32X52",  "Wellendichtring 32x52x10mm"),
    ("ART-041", "Motoröl 5W-40 vollsynth. 1L",   10.90,  19.90,   5, "4006501744445", "MO-5W40-1L",   "Vollsynthetisches Motoröl 5W-40, 1 Liter"),
    ("ART-042", "Kettenritzel vorn Z14",           12.00,  24.00,   5, "4047972755556", "KR-VORN-Z14",  "Antriebsritzel Z14, 520er Teilung"),
    ("ART-043", "Kettenrad hinten Z38",            28.00,  56.00,   3, "4047972766667", "KR-HINT-Z38",  "Hinterrad-Kettenrad Z38, Aluminium"),
    ("ART-044", "Kupplungszug",                    8.50,  17.00,   5, "4001171077778", "KZ-UNIVERSAL",  "Kupplungszug 1,2m mit Endstücken"),
    ("ART-045", "Gaszug",                          7.90,  15.90,   5, "4001171088889", "GZ-OFFEN-1M",  "Gaszug offen 1,0m Länge"),
    ("ART-046", "Bremsscheibenschloss",           14.00,  28.00,   3, "4047972899990", "SL-SCHRAUB-14","Bremsscheibenschloss Ø 14mm, orange"),
    ("ART-047", "Motorsport-Schraubenkit",        22.00,  45.00,   2, None,            "SK-TITAN-M6",  "Titanschraubenset M6, 50-teilig"),
    ("ART-048", "Reifenheber Satz",               12.00,  25.00,   2, None,            "RH-SATZ-3TLG", "3-teiliger Reifenheber aus Stahl"),
    ("ART-049", "Öl-Ablassschraube M12x1.5",       2.50,   5.90,  20, "4006501911101", "OA-M12X15-MG", "Magnetische Ölablassschraube M12x1,5"),
    ("ART-050", "Sicherheitsweste Kinder",        18.00,  39.90,   5, None,            "SV-KIND-EN13",  "Sicherheitsweste EN13158 Level 1, Größe S-M"),
]

CUSTOMERS_B2C = [
    ("Max",        "Müller",      "max.mueller@email.de",             "0171-1234567"),
    ("Anna",       "Schmidt",     "anna.schmidt@web.de",              "0172-2345678"),
    ("Thomas",     "Weber",       "thomas.weber@gmx.de",              "0173-3456789"),
    ("Laura",      "Fischer",     "laura.fischer@outlook.de",         "0174-4567890"),
    ("Michael",    "Bauer",       "michael.bauer@t-online.de",        "0175-5678901"),
    ("Sarah",      "Koch",        "sarah.koch@yahoo.de",              "0176-6789012"),
    ("Daniel",     "Richter",     "daniel.richter@mail.de",           "0177-7890123"),
    ("Julia",      "Klein",       "julia.klein@freenet.de",           "0178-8901234"),
    ("Stefan",     "Wolf",        "stefan.wolf@arcor.de",             "0179-9012345"),
    ("Christina",  "Schröder",    "christina.schroeder@posteo.de",    "0151-0123456"),
    ("Markus",     "Neumann",     "markus.neumann@proton.me",         "0152-1234567"),
    ("Katharina",  "Schwarz",     "katharina.schwarz@icloud.com",     "0153-2345678"),
    ("Andreas",    "Zimmermann",  "andreas.zimmermann@gmx.net",       "0154-3456789"),
    ("Lisa",       "Braun",       "lisa.braun@hotmail.de",            "0155-4567890"),
    ("Christian",  "Krüger",      "christian.krueger@live.de",        "0156-5678901"),
    ("Jennifer",   "Hartmann",    "jennifer.hartmann@email.com",      "0157-6789012"),
    ("Martin",     "Lange",       "martin.lange@web.de",              "0158-7890123"),
    ("Stefanie",   "Schmitt",     "stefanie.schmitt@t-online.de",     "0159-8901234"),
    ("Peter",      "Werner",      "peter.werner@gmx.de",              "0160-9012345"),
    ("Sabine",     "Schmid",      "sabine.schmid@outlook.com",        "0161-0123456"),
]

CUSTOMERS_B2B = [
    ("Quad-Rental Bayern GmbH",        "info@quad-rental-bayern.de",        "0911-123456"),
    ("Offroad Center Nord GmbH",        "verkauf@offroad-nord.de",           "040-2345678"),
    ("Moto-Service Thüringen",          "buero@moto-service-th.de",          "0361-3456789"),
    ("ATV-Parts Direct",                "order@atv-parts.de",                "0221-4567890"),
    ("Werkstatt Müller & Söhne",        "info@mueller-werkstatt.de",         "069-5678901"),
    ("Quad-Tours Schwarzwald",          "buchung@quad-tours.de",             "0761-6789012"),
    ("Motorrad-Zentrum Ost",            "kontakt@mz-ost.de",                 "030-7890123"),
    ("Ersatzteile Großhandel Süd",      "bestellung@ersatzteile-sued.de",    "089-8901234"),
    ("Freizeit-Fahrzeuge GmbH",         "verkauf@freizeit-fahrzeuge.de",     "0711-9012345"),
    ("Offroad-Profis Berlin",           "service@offroad-berlin.de",         "030-0123456"),
    ("Quad-Werkstatt Hamburg",          "info@quad-hamburg.de",              "040-1234567"),
    ("Moto-Partner Leipzig",            "partner@moto-leipzig.de",           "0341-2345678"),
    ("ATV-Service Rheinland",           "service@atv-rheinland.de",          "0211-3456789"),
    ("Zweirad-Center Dresden",          "center@zweirad-dresden.de",         "0351-4567890"),
    ("Quad-Station München",            "muenchen@quad-station.de",          "089-6789012"),
]

SUPPLIERS_DATA = [
    ("Motorex AG",               "bestellung@motorex.de",         "0800-123456",  "Klaus Berger",     "Industriestraße",  "5",  "4313", "Möhlin",         "Schweiz",     "Schmierstoffe und Öle"),
    ("Brembo S.p.A.",            "parts@brembo.de",               "0211-234567",  "Maria Rossi",      "Bremsweg",         "1",  "40213", "Düsseldorf",     "Deutschland", "Bremskomponenten"),
    ("NGK Spark Plugs",          "info@ngk-europe.de",            "02131-123456", "Hans König",       "Zündkerzenstr.",   "3",  "41460", "Neuss",          "Deutschland", "Zündkerzen und Sensoren"),
    ("Dunlop Reifen GmbH",       "reifenhandel@dunlop.de",        "0221-345678",  "Stefan Müller",    "Reifenallee",      "12", "50679", "Köln",           "Deutschland", "Motorrad- und Quadreifen"),
    ("KMC Chain GmbH",           "ketten@kmc-chain.de",           "06131-456789", "Li Wei",           "Kettenpfad",       "7",  "55116", "Mainz",          "Deutschland", "Antriebsketten und Ritzel"),
    ("Yuasa Battery Europe",     "akkus@yuasa.de",                "040-567890",   "James Brown",      "Akkustraße",       "2",  "20099", "Hamburg",        "Deutschland", "Starterbatterien"),
    ("Twin Air Filters",         "filter@twinair.nl",             "+31-12345678", "Jan van Dam",      "Filterweg",        "9",  None,    "Valkenswaard",   "Niederlande", "Luftfilter und Zubehör"),
    ("Maxxis Reifen",            "reifen@maxxis.de",              "06192-678901", "Tom Chang",        "Reifenring",       "4",  "65760", "Eschborn",       "Deutschland", "Reifen für ATV und Quad"),
    ("Putoline Oil",             "oele@putoline.de",              "05251-789012", "Dirk Scholten",    "Ölgasse",          "6",  "33102", "Paderborn",      "Deutschland", "Motoröle und Schmierstoffe"),
    ("Pro Taper",                "import@protaper.de",            "069-890123",   "Mike Johnson",     "Lenkerstraße",     "8",  "60313", "Frankfurt",      "Deutschland", "Lenker und Handprotektoren"),
    ("Renthal Ltd.",             "kontakt@renthal.de",            "030-901234",   "Peter Smith",      "Kettenplatz",      "3",  "10117", "Berlin",         "Deutschland", "Ritzel und Lenker"),
    ("SKF Group",                "lager@skf.de",                  "040-012345",   "Anna Larsson",     "Lagerstraße",      "21", "20095", "Hamburg",        "Deutschland", "Wälzlager und Dichtungen"),
    ("Gates Corporation",        "riemen@gates.de",               "0711-123450",  "Robert Gates",     "Riemenweg",        "5",  "70173", "Stuttgart",      "Deutschland", "Keilriemen und Antriebsriemen"),
    ("EBC Brakes",               "bremsen@ebc-brakes.de",         "089-234560",   "Ian Buckley",      "Bremsbelagweg",    "14", "80331", "München",        "Deutschland", "Hochleistungs-Bremsbeläge"),
    ("Hiflo Filtro",             "filter@hiflofiltro.de",         "0211-345670",  "Carlos Ruiz",      "Filterplatz",      "2",  "40213", "Düsseldorf",     "Deutschland", "Öl- und Luftfilter"),
    ("Motul SA",                 "motul@motul.de",                "06102-456780", "François Dupont",  "Ölstraße",         "10", "65205", "Wiesbaden",      "Deutschland", "Hochleistungsmotoröle"),
    ("Hella KGaA",               "elektro@hella.de",              "05251-567890", "Werner Hella",     "Lichtweg",         "33", "59552", "Lippstadt",      "Deutschland", "Elektrik und Beleuchtung"),
    ("Bosch GmbH",               "motorrad@bosch.de",             "0711-678901",  "Dieter Bosch",     "Boschstraße",      "1",  "70469", "Stuttgart",      "Deutschland", "Elektrik und Zündanlagen"),
    ("Kenda Rubber",             "reifen@kenda.de",               "06192-789012", "Kevin Chen",       "Reifenstraße",     "7",  "65760", "Eschborn",       "Deutschland", "ATV- und Quadreifen"),
    ("Wiseco Pistons",           "kolben@wiseco.de",              "069-890120",   "Tom Wiseman",      "Kolbenweg",        "3",  "60313", "Frankfurt",      "Deutschland", "Hochleistungskolben"),
    ("DID Ketten",               "ketten@did-chain.de",           "040-901230",   "Kenji Tanaka",     "Kettenring",       "5",  "20095", "Hamburg",        "Deutschland", "Motorradketten DID"),
    ("Ferodo Brake Pads",        "bremsen@ferodo.de",             "089-012340",   "Henri Martin",     "Bremsweg",         "8",  "80331", "München",        "Deutschland", "Bremsbeläge und Bremsscheiben"),
    ("Polisport",                "schutz@polisport.de",           "030-123450",   "Rui Santos",       "Schutzweg",        "4",  "10117", "Berlin",         "Deutschland", "Schutzausrüstung und Zubehör"),
    ("Acerbis Italy",            "acerbis@acerbis.de",            "0211-234570",  "Luca Bianchi",     "Tankweg",          "6",  "40213", "Düsseldorf",     "Deutschland", "Tanks, Schutz und Zubehör"),
    ("ProX Racing Parts",        "parts@prox.de",                 "0711-345680",  "Erik Jonkers",     "Rennweg",          "9",  "70173", "Stuttgart",      "Deutschland", "Kolben, Ventile und Lager"),
    ("Galfer Disc",              "bremsscheiben@galfer.de",       "089-456790",   "Jorge López",      "Scheibenstraße",   "2",  "80331", "München",        "Deutschland", "Bremsscheiben und Beläge"),
    ("Pivot Works",              "lager@pivotworks.de",           "040-567900",   "Chris Pivot",      "Lagerplatz",       "7",  "20099", "Hamburg",        "Deutschland", "Lenkkopflager und Radlager"),
    ("BikeMaster",               "zubehoer@bikemaster.de",        "06102-678910", "Mark Meier",       "Zubehörstraße",    "11", "65205", "Wiesbaden",      "Deutschland", "Motorrad-Zubehör allgemein"),
    ("Sunstar Sprockets",        "ritzel@sunstar.de",             "06192-789020", "Akira Suzuki",     "Ritzelweg",        "3",  "65760", "Eschborn",       "Deutschland", "Ritzel und Kettenräder"),
    ("Cometic Gasket",           "dichtungen@cometic.de",         "069-890130",   "Bill Combs",       "Dichtungsring",    "4",  "60313", "Frankfurt",      "Deutschland", "Motordichtungen und Dichtungssätze"),
]

COMPLAINTS = [
    "Ölwechsel und Inspektion",
    "Bremsen quietschen vorn",
    "Motor läuft unrund beim Kaltstart",
    "Kette muss gespannt und geschmiert werden",
    "Reifenwechsel vorn und hinten",
    "Getriebeöl wechseln – Intervall überschritten",
    "Zündkerzen wechseln – Leistungsverlust",
    "Große Inspektion laut Wartungsplan",
    "Kühlmittel verliert Druck",
    "Lichtmaschine prüfen – Batterie lädt nicht",
    "Stoßdämpfer hinten undicht",
    "Bremsflüssigkeit wechseln",
    "Luftfilter verschmutzt, Vergaser prüfen",
    "Kupplungsbeläge verschlissen",
    "Lenkkopflager ausgeschlagen",
    "Radlager vorn – Geräusch bei Kurvenfahrt",
    "Fehlercode auslesen – Motorwarnleuchte",
    "Schaltung hakt – Schaltung einstellen",
    "Kettenrad und Ritzel abgenutzt",
    "Starterbatterie leer – tauschen",
]

DOC_TYPES = [
    ("Fahrzeugschein.pdf",              "application/pdf"),
    ("Kaufvertrag.pdf",                 "application/pdf"),
    ("Versicherungspolice.pdf",         "application/pdf"),
    ("Inspektionsheft_Scan.pdf",        "application/pdf"),
    ("Rechnung_Lieferant.pdf",          "application/pdf"),
    ("Zulassungsbescheinigung.pdf",     "application/pdf"),
    ("Garantieurkunde.pdf",             "application/pdf"),
    ("Betriebsanleitung.pdf",           "application/pdf"),
    ("Wartungsprotokoll.pdf",           "application/pdf"),
    ("HU_Bescheinigung.pdf",            "application/pdf"),
    ("Foto_Fahrzeug_vorn.jpg",          "image/jpeg"),
    ("Foto_Fahrzeug_seite.jpg",         "image/jpeg"),
    ("Foto_Schaden.jpg",                "image/jpeg"),
    ("Kostenvoranschlag.pdf",           "application/pdf"),
    ("Lieferschein.pdf",                "application/pdf"),
]


# ---------------------------------------------------------------------------
# Seed-Funktionen
# ---------------------------------------------------------------------------

def seed_manufacturers(db):
    """Hersteller und Modelle."""
    created = 0
    for name in MANUFACTURERS:
        if db.query(Manufacturer).filter(Manufacturer.name == name).first():
            continue
        m = Manufacturer(name=name)
        db.add(m)
        db.flush()
        for model_name in MODELS.get(name, [f"{name} Modell 1", f"{name} Modell 2"]):
            if not db.query(VehicleModel).filter(
                VehicleModel.manufacturer_id == m.id,
                VehicleModel.name == model_name,
            ).first():
                db.add(VehicleModel(manufacturer_id=m.id, name=model_name))
        created += 1
    db.commit()
    print(f"  Hersteller: {created} neu")


def seed_suppliers(db):
    """50 Lieferanten mit vollständigen Kontaktdaten."""
    created = 0
    for name, email, phone, contact, street, hnr, plz, city, country, notes in SUPPLIERS_DATA:
        if db.query(Supplier).filter(Supplier.name == name).first():
            continue
        db.add(Supplier(
            name=name,
            email=email,
            phone=phone,
            contact_person=contact,
            street=street,
            house_number=hnr,
            postal_code=plz,
            city=city,
            country=country,
            notes=notes,
        ))
        created += 1
    db.commit()
    print(f"  Lieferanten: {created} neu (von {len(SUPPLIERS_DATA)} gesamt)")


def seed_customers(db):
    """Kunden mit Adressen."""
    created = 0
    for first, last, email, phone in CUSTOMERS_B2C:
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        c = Customer(customer_type="B2C", first_name=first, last_name=last,
                     email=email, phone=phone, is_active=True)
        db.add(c)
        db.flush()
        created += 1
        if random.random() < 0.6:
            addr = random.choice(ADDRESSES)
            db.add(CustomerAddress(customer_id=c.id,
                address_type=random.choice(["main", "billing"]),
                street=addr[0], house_number=addr[1],
                postal_code=addr[2], city=addr[3], country="Deutschland"))

    for company, email, phone in CUSTOMERS_B2B:
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        c = Customer(customer_type="B2B", company_name=company, email=email,
                     phone=phone,
                     vat_id=f"DE{random.randint(100000000, 999999999)}" if random.random() > 0.3 else None,
                     is_active=True)
        db.add(c)
        db.flush()
        created += 1
        if random.random() < 0.8:
            addr = random.choice(ADDRESSES)
            db.add(CustomerAddress(customer_id=c.id, address_type="billing",
                street=addr[0], house_number=addr[1],
                postal_code=addr[2], city=addr[3], country="Deutschland"))

    db.commit()
    print(f"  Kunden: {created} neu")


def seed_articles(db):
    """50 Artikel mit unterschiedlichen Attributen."""
    from app.models.article_category import ArticleCategory
    from app.models.supplier import Supplier

    suppliers = db.query(Supplier).all()
    categories = db.query(ArticleCategory).all()

    created = 0
    for art_nr, name, ek, vk, min_stock, barcode, oem, beschreibung in ARTICLES:
        if db.query(Article).filter(Article.article_number == art_nr).first():
            continue
        db.add(Article(
            article_number=art_nr,
            name=name,
            description=beschreibung,
            purchase_price=Decimal(str(ek)),
            sales_price_b2c=Decimal(str(vk)),
            sales_price_b2b=Decimal(str(round(vk * 0.88, 2))),
            vat_rate=Decimal("19"),
            stock_quantity=random.randint(0, 60),
            minimum_stock=min_stock,
            barcode=barcode,
            oem_number=oem,
            supplier_id=random.choice(suppliers).id if suppliers and random.random() > 0.2 else None,
            category_id=random.choice(categories).id if categories and random.random() > 0.3 else None,
        ))
        created += 1
    db.commit()
    print(f"  Artikel: {created} neu (von {len(ARTICLES)} gesamt)")


def seed_vehicles(db):
    """50 Fahrzeuge (verschiedene Hersteller, Modelle, Kunden)."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    manufacturers = db.query(Manufacturer).all()
    if not customers or not manufacturers:
        print("  Fahrzeuge: fehlende Abhängigkeiten – übersprungen")
        return

    existing = db.query(Vehicle).count()
    target = 50
    if existing >= target:
        print(f"  Fahrzeuge: bereits {existing} vorhanden")
        return

    colors = ["Schwarz", "Weiß", "Rot", "Blau", "Grün", "Silber", "Grau", "Gelb", "Orange", "Braun"]
    categories = ["quad", "quad", "quad", "motorcycle", "motorcycle"]

    for i in range(target - existing):
        c = random.choice(customers)
        m = random.choice(manufacturers)
        models = db.query(VehicleModel).filter(VehicleModel.manufacturer_id == m.id).all()
        vm = random.choice(models) if models and random.random() > 0.2 else None
        model_names = MODELS.get(m.name, [f"{m.name} Modell"])
        vin_suffix = f"{(existing + i + 1):015d}"

        v = Vehicle(
            customer_id=c.id,
            manufacturer_id=m.id,
            vehicle_model_id=vm.id if vm else None,
            model_name_free=random.choice(model_names) if not vm else None,
            category=random.choice(categories),
            build_year=random.randint(2010, 2024),
            vin=f"WVW{vin_suffix}",
            license_plate=f"QP-{1000 + existing + i}" if random.random() > 0.15 else None,
            mileage=random.randint(100, 55000) if random.random() > 0.05 else None,
            operating_hours=random.randint(10, 800) if random.random() > 0.5 else None,
            color=random.choice(colors),
            notes=random.choice([None, None, "Gepflegter Zustand", "Gebrauchtfahrzeug", "Unfallschäden repariert"]),
            is_active=random.random() > 0.05,
        )
        db.add(v)

    db.commit()
    print(f"  Fahrzeuge: {target - existing} neu")


def seed_maintenance_plans(db):
    """Wartungspläne pro Hersteller und Modell."""
    manufacturers = db.query(Manufacturer).all()
    if not manufacturers:
        return

    plans_data = [
        ("Kleine Inspektion",    "Ölwechsel, Filter prüfen, Sichtprüfung",          5000,  None, 12),
        ("Große Inspektion",     "Vollständige Durchsicht, alle Verbrauchsteile",    10000, None, 24),
        ("Bremsen-Service",      "Bremsbeläge, Bremsflüssigkeit, Scheiben prüfen",  20000, None, None),
        ("Getriebe-Service",     "Getriebeöl wechseln, Schaltung prüfen",           15000, 500,  None),
        ("Kettensatz-Wartung",   "Kette spannen, ölen, Ritzel prüfen",               3000, 100,  None),
    ]
    task_lists = {
        "Kleine Inspektion":  ["Motoröl wechseln", "Ölfilter tauschen", "Luftfilter prüfen", "Reifendruck prüfen"],
        "Große Inspektion":   ["Alle Flüssigkeiten wechseln", "Bremsbeläge messen", "Ventilspiel prüfen", "Zündkerzen tauschen", "Kette und Ritzel prüfen"],
        "Bremsen-Service":    ["Bremsflüssigkeit ablassen", "Neue DOT4 einfüllen", "Bremsbeläge messen", "Bremsscheiben auf Verschleiß prüfen"],
        "Getriebe-Service":   ["Getriebeöl ablassen", "Neues 75W-90 einfüllen", "Schaltung einstellen"],
        "Kettensatz-Wartung": ["Kettenspannung messen", "Kette ölen", "Ritzel auf Abnutzung prüfen"],
    }
    created = 0
    for m in manufacturers[:12]:
        models = db.query(VehicleModel).filter(VehicleModel.manufacturer_id == m.id).limit(3).all()
        for plan_name, desc, km, hrs, months in plans_data:
            vm_id = random.choice(models).id if models and random.random() > 0.3 else None
            if db.query(MaintenancePlan).filter(
                MaintenancePlan.manufacturer_id == m.id,
                MaintenancePlan.name == plan_name,
                MaintenancePlan.vehicle_model_id == vm_id,
            ).first():
                continue
            p = MaintenancePlan(
                manufacturer_id=m.id,
                vehicle_model_id=vm_id,
                name=plan_name,
                description=desc,
                interval_km=km,
                interval_hours=hrs,
                interval_months=months,
            )
            db.add(p)
            db.flush()
            for idx, task_name in enumerate(task_lists.get(plan_name, ["Prüfen", "Warten"])):
                db.add(MaintenanceTask(maintenance_plan_id=p.id, name=task_name, sort_order=idx))
            created += 1
    db.commit()
    print(f"  Wartungspläne: {created} neu")


def seed_appointments(db):
    """Termine in Vergangenheit und Zukunft."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not vehicles or not admin:
        print("  Termine: fehlende Abhängigkeiten – übersprungen")
        return

    existing = db.query(Appointment).count()
    target = 30
    if existing >= target:
        print(f"  Termine: bereits {existing} vorhanden")
        return

    now = datetime.now(timezone.utc)
    for i in range(target - existing):
        c = random.choice(customers)
        v_list = [x for x in vehicles if x.customer_id == c.id]
        v = random.choice(v_list) if v_list else random.choice(vehicles)
        apt_type = random.choice(["workshop", "workshop", "workshop", "test_drive"])
        if random.random() < 0.55:
            days_off = -random.randint(1, 120)
            status = random.choice(["completed", "completed", "cancelled"])
        else:
            days_off = random.randint(1, 90)
            status = random.choice(["planned", "confirmed", "planned"])

        start = (now + timedelta(days=days_off)).replace(
            hour=8 + (i % 9), minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=random.choice([1, 2, 3]))

        db.add(Appointment(
            customer_id=c.id,
            vehicle_id=v.id,
            appointment_type=apt_type,
            source="internal",
            status=status,
            title=f"{'Werkstatt' if apt_type == 'workshop' else 'Probefahrt'} – {v.license_plate or 'Fahrzeug'}",
            starts_at=start,
            ends_at=end,
            created_by=admin.id,
        ))
    db.commit()
    print(f"  Termine: {target - existing} neu")


def _find_plan(db, vehicle_id) -> MaintenancePlan | None:
    """Passenden Wartungsplan für Fahrzeug suchen."""
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        return None
    if v.vehicle_model_id:
        p = db.query(MaintenancePlan).filter(
            MaintenancePlan.manufacturer_id == v.manufacturer_id,
            MaintenancePlan.vehicle_model_id == v.vehicle_model_id,
        ).first()
        if p:
            return p
    return db.query(MaintenancePlan).filter(
        MaintenancePlan.manufacturer_id == v.manufacturer_id,
        MaintenancePlan.vehicle_model_id.is_(None),
    ).first()


def seed_workshop_orders(db):
    """50 Werkstattaufträge mit allen Status, inkl. Wartungsplan-Verknüpfung."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()
    articles = db.query(Article).filter(Article.is_active == True).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not vehicles or not articles or not admin:
        print("  Werkstattaufträge: fehlende Abhängigkeiten – übersprungen")
        return

    existing = db.query(WorkshopOrder).count()
    target = 50
    if existing >= target:
        print(f"  Werkstattaufträge: bereits {existing} vorhanden")
        return

    # Status-Verteilung: jeder Status gut vertreten
    status_pool = (
        ["new"] * 8 +
        ["planned"] * 8 +
        ["in_progress"] * 10 +
        ["completed"] * 12 +
        ["invoiced"] * 8 +
        ["cancelled"] * 4
    )
    random.shuffle(status_pool)
    year = datetime.now().year

    for i in range(target - existing):
        c = random.choice(customers)
        v_list = [x for x in vehicles if x.customer_id == c.id]
        v = random.choice(v_list) if v_list else random.choice(vehicles)
        status = status_pool[i % len(status_pool)]
        plan = _find_plan(db, v.id)

        created_days_ago = random.randint(0, 180)
        order = WorkshopOrder(
            customer_id=c.id,
            vehicle_id=v.id,
            maintenance_plan_id=plan.id if plan else None,
            order_number=f"WO-{year}-{5000 + existing + i:04d}",
            status=status,
            complaint_description=random.choice(COMPLAINTS),
            mileage_at_checkin=v.mileage,
            estimated_work_minutes=random.choice([60, 90, 120, 180, 240]),
            actual_work_minutes=random.choice([45, 75, 110, 160, 210]) if status in ("completed", "invoiced") else None,
            created_by=admin.id,
        )
        db.add(order)
        db.flush()

        # 2–4 Positionen pro Auftrag
        num_items = random.randint(2, 4)
        art_sample = random.sample(articles, min(num_items - 1, len(articles)))
        for a in art_sample:
            qty = Decimal(str(round(random.uniform(1, 3), 0)))
            db.add(WorkshopOrderItem(
                workshop_order_id=order.id,
                item_type="material",
                article_id=a.id,
                description=a.name,
                quantity=qty,
                unit="Stück",
                unit_price=a.sales_price_b2c,
                vat_rate=Decimal("19"),
                source="manual",
            ))
        # Arbeitszeit
        hours = Decimal(str(round(random.uniform(0.5, 4.0), 1)))
        db.add(WorkshopOrderItem(
            workshop_order_id=order.id,
            item_type="labor",
            description="Arbeitszeit Mechaniker",
            quantity=hours,
            unit="Stunde",
            unit_price=Decimal("89.00"),
            vat_rate=Decimal("19"),
            source="manual",
        ))

    db.commit()
    print(f"  Werkstattaufträge: {target - existing} neu (alle Status, mit Wartungsplan-Verknüpfung)")


def seed_invoices(db):
    """50 Rechnungen mit verschiedenen Status inkl. Stornorechnungen."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    orders_completed = db.query(WorkshopOrder).filter(
        WorkshopOrder.status.in_(["completed", "invoiced"])
    ).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not admin:
        print("  Rechnungen: fehlende Abhängigkeiten – übersprungen")
        return

    existing = db.query(Invoice).count()
    target = 50
    if existing >= target:
        print(f"  Rechnungen: bereits {existing} vorhanden")
        return

    year = datetime.now().year

    # Status-Verteilung
    status_pool = (
        ["draft"] * 6 +
        ["issued"] * 12 +
        ["partially_paid"] * 5 +
        ["paid"] * 15 +
        ["cancelled"] * 6
    )
    random.shuffle(status_pool)

    storno_count = 0
    for i in range(target - existing):
        c = random.choice(customers)
        wo = random.choice(orders_completed) if orders_completed and random.random() < 0.5 else None
        status = status_pool[i % len(status_pool)]
        inv_date = date.today() - timedelta(days=random.randint(0, 180))
        due = inv_date + timedelta(days=14)

        net = Decimal(str(round(random.uniform(80, 1500), 2)))
        vat = (net * Decimal("0.19")).quantize(Decimal("0.01"))
        gross = net + vat

        inv_number = f"RE-{year}-{3000 + existing + i:04d}"
        inv = Invoice(
            customer_id=c.id,
            workshop_order_id=wo.id if wo else None,
            invoice_number=inv_number,
            invoice_date=inv_date,
            due_date=due,
            status=status,
            currency="EUR",
            net_amount=net,
            vat_amount=vat,
            gross_amount=gross,
            payment_method="Überweisung" if status == "paid" else None,
            reminder_level=random.choice([0, 0, 1, 2]) if status in ("issued", "partially_paid") else 0,
            notes="Automatisch generierter Testdatensatz",
            created_by=admin.id,
        )
        db.add(inv)
        db.flush()

        # Positionen
        for j in range(random.randint(1, 3)):
            pos_net = Decimal(str(round(float(net) / (j + 1), 2)))
            db.add(InvoiceItem(
                invoice_id=inv.id,
                description=random.choice(["Werkstattleistung", "Ersatzteil", "Arbeitszeit", "Material", "Inspektion"]),
                quantity=Decimal(str(random.randint(1, 3))),
                unit=random.choice(["Stück", "Stunde", "Pauschale"]),
                unit_price=pos_net,
                vat_rate=Decimal("19"),
                line_total_net=pos_net,
            ))

        # Für stornierte Rechnungen: Stornorechnung anlegen
        if status == "cancelled" and storno_count < 6:
            sto_number = f"STO-{year}-{storno_count + 1:04d}"
            if not db.query(Invoice).filter(Invoice.invoice_number == sto_number).first():
                storno = Invoice(
                    customer_id=c.id,
                    workshop_order_id=None,
                    cancellation_of_id=inv.id,
                    invoice_number=sto_number,
                    invoice_date=date.today(),
                    due_date=date.today(),
                    status="issued",
                    currency="EUR",
                    net_amount=-net,
                    vat_amount=-vat,
                    gross_amount=-gross,
                    notes=f"Stornorechnung zu {inv_number}",
                    created_by=admin.id,
                )
                db.add(storno)
                db.flush()
                for item in inv.items:
                    db.add(InvoiceItem(
                        invoice_id=storno.id,
                        description=item.description,
                        quantity=-item.quantity,
                        unit=item.unit,
                        unit_price=item.unit_price,
                        vat_rate=item.vat_rate,
                        line_total_net=-item.line_total_net,
                    ))
                inv.cancellation_invoice_id = storno.id
                storno_count += 1

    db.commit()
    print(f"  Rechnungen: {target - existing} neu ({storno_count} Stornorechnungen enthalten)")


def seed_documents(db):
    """50 Dokumente (verschiedene Typen, Kunden, Fahrzeuge)."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not admin:
        print("  Dokumente: fehlende Abhängigkeiten – übersprungen")
        return

    upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    existing = db.query(Document).count()
    target = 50
    if existing >= target:
        print(f"  Dokumente: bereits {existing} vorhanden")
        return

    for i in range(target - existing):
        c = random.choice(customers)
        v_list = [x for x in vehicles if x.customer_id == c.id]
        v = random.choice(v_list) if v_list and random.random() > 0.25 else None
        fname, ctype = random.choice(DOC_TYPES)

        # Eindeutiger Dateiname
        unique_name = f"seed_{uuid.uuid4().hex[:10]}_{fname}"
        full_path = Path(upload_dir) / unique_name

        # Platzhalterinhalt je nach Typ
        if ctype == "application/pdf":
            content = (
                f"%PDF-1.4 Platzhalter\n"
                f"Dokument: {fname}\n"
                f"Kunde: {c.first_name or c.company_name or ''} {c.last_name or ''}\n"
                f"Fahrzeug: {v.vin if v else 'keines'}\n"
                f"Seed-Index: {existing + i + 1}\n"
            ).encode("utf-8")
        else:
            # Minimales JPEG-Platzhalter-Byte (damit es nicht 0 Bytes groß ist)
            content = (
                f"IMG-PLATZHALTER {fname} Kunde:{c.id} Fahrzeug:{v.id if v else '-'}"
            ).encode("utf-8")

        full_path.write_bytes(content)

        db.add(Document(
            customer_id=c.id,
            vehicle_id=v.id if v else None,
            filename=fname,
            content_type=ctype,
            file_path=str(full_path),
            file_size=len(content),
            created_by=admin.id,
        ))

    db.commit()
    print(f"  Dokumente: {target - existing} neu (versch. Typen und Fahrzeuge)")


def seed_audit_logs(db):
    """Audit-Log-Einträge."""
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not admin:
        print("  Audit Logs: kein Admin-User")
        return

    existing = db.query(AuditLog).count()
    target = 40
    if existing >= target:
        print(f"  Audit Logs: bereits {existing} vorhanden")
        return

    actions = [
        ("customer",       "create",  {"email": "neu@example.de"}, None),
        ("customer",       "update",  {"phone": "0171-9999999"}, {"phone": "0171-0000000"}),
        ("vehicle",        "create",  {"vin": "WVW123456789"}, None),
        ("vehicle",        "update",  {"mileage": 18000}, {"mileage": 15000}),
        ("workshop_order", "create",  {"order_number": "WO-2026-0001"}, None),
        ("workshop_order", "update",  {"status": "completed"}, {"status": "in_progress"}),
        ("invoice",        "create",  {"invoice_number": "RE-2026-0001"}, None),
        ("invoice",        "issue",   None, None),
        ("invoice",        "cancel",  {"reason": "Falsche Positionen"}, None),
        ("user",           "login",   None, None),
        ("settings",       "update",  {"company_name": "Quad Paradies Schoner"}, None),
        ("document",       "upload",  {"filename": "Fahrzeugschein.pdf"}, None),
        ("document",       "delete",  None, {"filename": "Altdokument.pdf"}),
    ]

    for i in range(target - existing):
        act = actions[i % len(actions)]
        db.add(AuditLog(
            user_id=admin.id,
            entity_type=act[0],
            action=act[1],
            old_values=act[3],
            new_values=act[2],
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            user_agent="Seed-Script/1.0",
        ))
    db.commit()
    print(f"  Audit Logs: {target - existing} neu")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main():
    db = SessionLocal()
    try:
        print("═" * 50)
        print("  WareVision Seed-Script – 50er Testdatensätze")
        print("═" * 50)
        seed_manufacturers(db)
        seed_suppliers(db)
        seed_customers(db)
        seed_articles(db)
        seed_vehicles(db)
        seed_maintenance_plans(db)
        seed_appointments(db)
        seed_workshop_orders(db)
        seed_invoices(db)
        seed_documents(db)
        seed_audit_logs(db)
        print("═" * 50)
        print("  Seed erfolgreich abgeschlossen.")
        print("═" * 50)
    except Exception as e:
        db.rollback()
        print(f"FEHLER: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
