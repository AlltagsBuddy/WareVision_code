"""Seed demo data: Artikel, Kunden, Fahrzeuge, Hersteller (je mind. 25)."""

import random
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.article import Article
from app.models.customer import Customer
from app.models.manufacturer import Manufacturer, VehicleModel
from app.models.vehicle import Vehicle


# Hersteller (Quad/Motorrad)
MANUFACTURERS = [
    "Yamaha", "Honda", "Kawasaki", "Suzuki", "KTM", "CFMOTO", "Polaris",
    "Can-Am", "Arctic Cat", "Husqvarna Motorcycles", "BMW Motorrad",
    "Ducati", "Triumph", "Aprilia", "Beta", "Sherco", "GasGas",
    "Benelli", "Royal Enfield", "Indian", "Harley-Davidson",
    "Husaberg", "TM Racing", "Fantic", "Rieju",
]

# Fahrzeugmodelle pro Hersteller (Name)
MODELS = {
    "Yamaha": ["Grizzly 700", "Kodiak 450", "Raptor 700", "YFZ450", "Wolverine", "Kodiak 700", "Grizzly 450"],
    "Honda": ["Foreman", "Rancher", "Pioneer", "Talon", "Ruben", "TRX420", "TRX250"],
    "Kawasaki": ["Brute Force", "Mule", "Teryx", "KFX", "KLR650", "Z900", "Ninja 400"],
    "Suzuki": ["King Quad", "QuadSport", "DR650", "V-Strom", "GSX-R", "Hayabusa"],
    "KTM": ["XCF", "EXC", "SX-F", "Freeride", "1290 Super Duke", "390 Duke"],
    "CFMOTO": ["CForce", "ZForce", "UForce", "450", "625", "800"],
    "Polaris": ["Sportsman", "Ranger", "RZR", "Scrambler", "General", "Ace"],
    "Can-Am": ["Outlander", "Renegade", "Maverick", "Defender", "Commander"],
    "Husqvarna Motorcycles": ["TE", "FE", "TC", "FC", "Svartpilen", "Vitpilen"],
    "BMW Motorrad": ["R1250GS", "S1000RR", "F850GS", "R18", "C400X"],
    "Ducati": ["Panigale", "Monster", "Scrambler", "Multistrada", "Diavel"],
    "Triumph": ["Tiger", "Street Triple", "Bonneville", "Scrambler", "Rocket"],
    "Aprilia": ["RSV4", "Tuono", "Dorsoduro", "Shiver", "SXR"],
    "Beta": ["RR", "Xtrainer", "Alp", "Revolution"],
    "Sherco": ["SE", "SER", "ST", "X-Ride"],
    "GasGas": ["EC", "MC", "TX", "SM"],
    "Benelli": ["TRK", "Leoncino", "Imperiale", "BN"],
    "Royal Enfield": ["Himalayan", "Interceptor", "Classic", "Meteor"],
    "Indian": ["Scout", "Chief", "FTR", "Challenger"],
    "Harley-Davidson": ["Sportster", "Softail", "Touring", "Street"],
    "Husaberg": ["FE", "TE", "FX"],
    "TM Racing": ["EN", "MX", "SM"],
    "Fantic": ["Caballero", "XEF", "XX"],
    "Rieju": ["MR", "MRT", "Tango"],
    "Arctic Cat": ["Alterra", "DVX", "Thundercat"],
}

# Artikel (Werkstatt/Ersatzteile)
ARTICLES = [
    ("ART-001", "Motoröl 10W-40 4L", "Synthetisches Motoröl", 24.90, 34.90),
    ("ART-002", "Ölfilter Standard", "Universal-Ölfilter", 4.50, 9.90),
    ("ART-003", "Luftfilter", "Papier-Luftfilter", 8.90, 18.90),
    ("ART-004", "Bremsscheibe vorn", "Vorderrad Bremsscheibe", 45.00, 89.00),
    ("ART-005", "Bremsbeläge Satz", "Vorder- und Hinterrad", 28.00, 55.00),
    ("ART-006", "Zündkerze NGK", "Standard-Zündkerze", 3.50, 7.90),
    ("ART-007", "Keilriemen", "Antriebsriemen", 18.00, 38.00),
    ("ART-008", "Kupplungsbelag Satz", "Kupplungsscheiben", 65.00, 125.00),
    ("ART-009", "Getriebeöl 1L", "SAE 80W-90", 12.00, 22.00),
    ("ART-010", "Kühlmittel 5L", "Frostschutz -25°C", 18.00, 32.00),
    ("ART-011", "Bremsflüssigkeit DOT4", "500ml", 6.50, 12.90),
    ("ART-012", "Fett Kartanwellen", "Universal-Fett", 8.00, 15.00),
    ("ART-013", "Luftfilter Ölbad", "Ölbad-Luftfilter", 22.00, 45.00),
    ("ART-014", "Starterbatterie 12V", "12Ah", 45.00, 89.00),
    ("ART-015", "Reifen vorn 25x8-12", "ATV Vorderreifen", 55.00, 110.00),
    ("ART-016", "Reifen hinten 25x10-12", "ATV Hinterreifen", 65.00, 130.00),
    ("ART-017", "Schlauch innen", "Reifen-Schlauch", 12.00, 24.00),
    ("ART-018", "Bremsflüssigkeit DOT5.1", "500ml", 9.00, 18.00),
    ("ART-019", "Kettensatz", "Antriebskette mit Ritzeln", 85.00, 165.00),
    ("ART-020", "Kettenöl Spray", "400ml", 8.50, 16.90),
    ("ART-021", "Scheibenwischer 18\"", "Frontscheibe", 6.00, 12.00),
    ("ART-022", "Scheibenwischer-Flüssigkeit", "5L Konzentrat", 5.00, 10.00),
    ("ART-023", "Zündspule", "Hochspannungsspule", 35.00, 68.00),
    ("ART-024", "Zündkabel Satz", "4 Zylinder", 18.00, 35.00),
    ("ART-025", "Dichtung Zylinderkopf", "Kopfdichtung", 22.00, 45.00),
    ("ART-026", "Ventilführungsdichtung", "Einzelstück", 4.00, 8.50),
    ("ART-027", "Kupplungshebel", "Ersatzhebel", 12.00, 25.00),
    ("ART-028", "Bremshebel vorn", "Vorderradbremse", 15.00, 32.00),
    ("ART-029", "Rückspiegel Paar", "Universal", 18.00, 38.00),
    ("ART-030", "Fußrasten Satz", "Alu-Fußrasten", 45.00, 95.00),
]

# Kunden (B2C + B2B)
CUSTOMERS_B2C = [
    ("Max", "Müller", "max.mueller@email.de", "0171-1234567"),
    ("Anna", "Schmidt", "anna.schmidt@web.de", "0172-2345678"),
    ("Thomas", "Weber", "thomas.weber@gmx.de", "0173-3456789"),
    ("Laura", "Fischer", "laura.fischer@outlook.de", "0174-4567890"),
    ("Michael", "Bauer", "michael.bauer@t-online.de", "0175-5678901"),
    ("Sarah", "Koch", "sarah.koch@yahoo.de", "0176-6789012"),
    ("Daniel", "Richter", "daniel.richter@mail.de", "0177-7890123"),
    ("Julia", "Klein", "julia.klein@freenet.de", "0178-8901234"),
    ("Stefan", "Wolf", "stefan.wolf@arcor.de", "0179-9012345"),
    ("Christina", "Schröder", "christina.schroeder@posteo.de", "0151-0123456"),
    ("Markus", "Neumann", "markus.neumann@proton.me", "0152-1234567"),
    ("Katharina", "Schwarz", "katharina.schwarz@icloud.com", "0153-2345678"),
    ("Andreas", "Zimmermann", "andreas.zimmermann@gmx.net", "0154-3456789"),
    ("Lisa", "Braun", "lisa.braun@hotmail.de", "0155-4567890"),
    ("Christian", "Krüger", "christian.krueger@live.de", "0156-5678901"),
    ("Jennifer", "Hartmann", "jennifer.hartmann@email.com", "0157-6789012"),
    ("Martin", "Lange", "martin.lange@web.de", "0158-7890123"),
    ("Stefanie", "Schmitt", "stefanie.schmitt@t-online.de", "0159-8901234"),
    ("Peter", "Werner", "peter.werner@gmx.de", "0160-9012345"),
    ("Sabine", "Schmid", "sabine.schmid@outlook.com", "0161-0123456"),
    ("Klaus", "Krause", "klaus.krause@freenet.de", "0162-1234567"),
    ("Monika", "Meier", "monika.meier@arcor.de", "0163-2345678"),
    ("Frank", "Huber", "frank.huber@posteo.de", "0164-3456789"),
    ("Petra", "Lehmann", "petra.lehmann@proton.me", "0165-4567890"),
    ("Uwe", "Hermann", "uwe.hermann@icloud.com", "0166-5678901"),
]

CUSTOMERS_B2B = [
    ("Quad-Rental Bayern GmbH", "info@quad-rental-bayern.de", "0911-123456"),
    ("Offroad Center Nord GmbH", "verkauf@offroad-nord.de", "040-2345678"),
    ("Moto-Service Thüringen", "buero@moto-service-th.de", "0361-3456789"),
    ("ATV-Parts Direct", "order@atv-parts.de", "0221-4567890"),
    ("Werkstatt Müller & Söhne", "info@mueller-werkstatt.de", "069-5678901"),
    ("Quad-Tours Schwarzwald", "buchung@quad-tours.de", "0761-6789012"),
    ("Motorrad-Zentrum Ost", "kontakt@mz-ost.de", "030-7890123"),
    ("Ersatzteile Großhandel Süd", "bestellung@ersatzteile-sued.de", "089-8901234"),
    ("Freizeit-Fahrzeuge GmbH", "verkauf@freizeit-fahrzeuge.de", "0711-9012345"),
    ("Offroad-Profis Berlin", "service@offroad-berlin.de", "030-0123456"),
    ("Quad-Werkstatt Hamburg", "info@quad-hamburg.de", "040-1234567"),
    ("Moto-Partner Leipzig", "partner@moto-leipzig.de", "0341-2345678"),
    ("ATV-Service Rheinland", "service@atv-rheinland.de", "0211-3456789"),
    ("Zweirad-Center Dresden", "center@zweirad-dresden.de", "0351-4567890"),
    ("Freizeit-Mobile Nürnberg", "nbg@freizeit-mobile.de", "0911-5678901"),
    ("Quad-Station München", "muenchen@quad-station.de", "089-6789012"),
    ("Offroad-Express GmbH", "express@offroad-express.de", "0511-7890123"),
    ("Moto-Depot Stuttgart", "depot@moto-stuttgart.de", "0711-8901234"),
    ("ATV-Handel West", "west@atv-handel.de", "0211-9012345"),
    ("Werkstatt-Service Köln", "koeln@werkstatt-service.de", "0221-0123456"),
    ("Quad-Rental Allgäu", "allgaeu@quad-rental.de", "0831-1234567"),
    ("Motorrad-Teile Groß", "gross@moto-teile.de", "0611-2345678"),
    ("Offroad-Zentrum Ruhr", "ruhr@offroad-zentrum.de", "0201-3456789"),
    ("Freizeit-Quads GmbH", "info@freizeit-quads.de", "0521-4567890"),
    ("Moto-Expert Frankfurt", "frankfurt@moto-expert.de", "069-5678901"),
]


def seed_manufacturers(db):
    """Create manufacturers."""
    created = 0
    for name in MANUFACTURERS:
        if db.query(Manufacturer).filter(Manufacturer.name == name).first():
            continue
        m = Manufacturer(name=name)
        db.add(m)
        db.flush()
        for model_name in MODELS.get(name, [name + " Modell 1", name + " Modell 2"]):
            if not db.query(VehicleModel).filter(
                VehicleModel.manufacturer_id == m.id,
                VehicleModel.name == model_name,
            ).first():
                db.add(VehicleModel(manufacturer_id=m.id, name=model_name))
        created += 1
    db.commit()
    print(f"Hersteller: {created} neu, {len(MANUFACTURERS)} gesamt")


def seed_customers(db):
    """Create customers."""
    created = 0
    for first, last, email, phone in CUSTOMERS_B2C:
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        db.add(Customer(
            customer_type="B2C",
            first_name=first,
            last_name=last,
            email=email,
            phone=phone,
        ))
        created += 1
    for company, email, phone in CUSTOMERS_B2B:
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        db.add(Customer(
            customer_type="B2B",
            company_name=company,
            email=email,
            phone=phone,
        ))
        created += 1
    db.commit()
    print(f"Kunden: {created} neu, {len(CUSTOMERS_B2C) + len(CUSTOMERS_B2B)} gesamt")


def seed_articles(db):
    """Create articles with stock."""
    created = 0
    for art_nr, name, desc, ek, vk in ARTICLES:
        if db.query(Article).filter(Article.article_number == art_nr).first():
            continue
        stock = random.randint(0, 50) if random.random() > 0.3 else random.randint(0, 5)
        min_stock = random.choice([0, 0, 0, 5, 10])
        db.add(Article(
            article_number=art_nr,
            name=name,
            description=desc,
            purchase_price=Decimal(str(ek)),
            sales_price_b2c=Decimal(str(vk)),
            sales_price_b2b=Decimal(str(round(vk * 0.92, 2))),
            vat_rate=Decimal("19"),
            stock_quantity=stock,
            minimum_stock=min_stock,
            barcode=f"400{random.randint(1000000000, 9999999999)}" if random.random() > 0.5 else None,
        ))
        created += 1
    db.commit()
    print(f"Artikel: {created} neu, {len(ARTICLES)} gesamt")


def seed_vehicles(db):
    """Create vehicles (needs customers and manufacturers)."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    manufacturers = db.query(Manufacturer).all()
    if not customers or not manufacturers:
        print("Keine Kunden oder Hersteller – Fahrzeuge übersprungen")
        return

    existing = db.query(Vehicle).count()
    target = 25
    if existing >= target:
        print(f"Fahrzeuge: bereits {existing} vorhanden")
        return

    colors = ["Schwarz", "Weiß", "Rot", "Blau", "Grün", "Silber", "Grau", "Gelb", "Orange"]
    plates = [f"AT-{random.randint(1000, 9999)}" for _ in range(50)]
    vins = [f"WVW{random.randint(1000000000000000, 9999999999999999)}" for _ in range(50)]

    created = 0
    used_plates = set()
    used_vins = set()
    for i in range(target - existing):
        c = random.choice(customers)
        m = random.choice(manufacturers)
        models = db.query(VehicleModel).filter(VehicleModel.manufacturer_id == m.id).all()
        vm = random.choice(models) if models else None
        model_names = MODELS.get(m.name, [f"{m.name} Modell"])
        model_free = random.choice(model_names) if model_names else f"{m.name} Standard"

        vin = f"WVW{1000000000000000 + i * 123456789}" if i < 30 else None
        plate = f"AT-{4000 + i}" if random.random() > 0.2 else None
        if plate and plate in used_plates:
            plate = f"AT-{5000 + i}"
        if plate:
            used_plates.add(plate)
        if vin:
            used_vins.add(vin)

        v = Vehicle(
            customer_id=c.id,
            manufacturer_id=m.id,
            vehicle_model_id=vm.id if vm else None,
            model_name_free=model_free if not vm else None,
            category=random.choice(["quad", "motorcycle"]),
            build_year=random.randint(2015, 2024),
            vin=vin,
            license_plate=plate,
            mileage=random.randint(500, 45000) if random.random() > 0.1 else None,
            color=random.choice(colors),
        )
        db.add(v)
        created += 1

    db.commit()
    print(f"Fahrzeuge: {created} neu, {existing + created} gesamt")


def main():
    db = SessionLocal()
    try:
        print("Seed startet...")
        seed_manufacturers(db)
        seed_customers(db)
        seed_articles(db)
        seed_vehicles(db)
        print("Seed abgeschlossen.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
