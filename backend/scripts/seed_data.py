"""Seed demo data: Kunden (mit Adressen, deaktiviert, gelöscht), Fahrzeuge, Werkverträge,
Werkstattaufträge, Termine, Rechnungen, Dokumente, Audit Logs."""

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
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem

# --- Adressen für Kunden ---
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
]

# --- Hersteller ---
MANUFACTURERS = [
    "Yamaha", "Honda", "Kawasaki", "Suzuki", "KTM", "CFMOTO", "Polaris",
    "Can-Am", "Arctic Cat", "Husqvarna Motorcycles", "BMW Motorrad",
    "Ducati", "Triumph", "Aprilia", "Beta", "Sherco", "GasGas",
    "Benelli", "Royal Enfield", "Indian", "Harley-Davidson",
    "Husaberg", "TM Racing", "Fantic", "Rieju",
]

MODELS = {
    "Yamaha": ["Grizzly 700", "Kodiak 450", "Raptor 700", "YFZ450", "Wolverine"],
    "Honda": ["Foreman", "Rancher", "Pioneer", "Talon", "TRX420"],
    "Kawasaki": ["Brute Force", "Mule", "Teryx", "KFX", "KLR650"],
    "Suzuki": ["King Quad", "QuadSport", "DR650", "V-Strom", "GSX-R"],
    "KTM": ["XCF", "EXC", "SX-F", "Freeride", "1290 Super Duke"],
    "CFMOTO": ["CForce", "ZForce", "UForce", "450", "625"],
    "Polaris": ["Sportsman", "Ranger", "RZR", "Scrambler", "General"],
    "Can-Am": ["Outlander", "Renegade", "Maverick", "Defender", "Commander"],
    "BMW Motorrad": ["R1250GS", "S1000RR", "F850GS", "R18"],
    "Ducati": ["Panigale", "Monster", "Scrambler", "Multistrada"],
}

# --- Artikel ---
ARTICLES = [
    ("ART-001", "Motoröl 10W-40 4L", 24.90, 34.90),
    ("ART-002", "Ölfilter Standard", 4.50, 9.90),
    ("ART-003", "Luftfilter", 8.90, 18.90),
    ("ART-004", "Bremsscheibe vorn", 45.00, 89.00),
    ("ART-005", "Bremsbeläge Satz", 28.00, 55.00),
    ("ART-006", "Zündkerze NGK", 3.50, 7.90),
    ("ART-007", "Keilriemen", 18.00, 38.00),
    ("ART-008", "Kupplungsbelag Satz", 65.00, 125.00),
    ("ART-009", "Getriebeöl 1L", 12.00, 22.00),
    ("ART-010", "Kühlmittel 5L", 18.00, 32.00),
    ("ART-011", "Bremsflüssigkeit DOT4", 6.50, 12.90),
    ("ART-012", "Fett Kartanwellen", 8.00, 15.00),
    ("ART-013", "Luftfilter Ölbad", 22.00, 45.00),
    ("ART-014", "Starterbatterie 12V", 45.00, 89.00),
    ("ART-015", "Reifen vorn 25x8-12", 55.00, 110.00),
    ("ART-016", "Reifen hinten 25x10-12", 65.00, 130.00),
    ("ART-017", "Schlauch innen", 12.00, 24.00),
    ("ART-018", "Bremsflüssigkeit DOT5.1", 9.00, 18.00),
    ("ART-019", "Kettensatz", 85.00, 165.00),
    ("ART-020", "Kettenöl Spray", 8.50, 16.90),
]

# --- Kunden B2C ---
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
]

# --- Kunden B2B ---
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
    ("Quad-Station München", "muenchen@quad-station.de", "089-6789012"),
]


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
    print(f"Hersteller: {created} neu")


def seed_customers(db):
    """Kunden mit Adressen, deaktivierte, gelöschte (anonymisiert)."""
    created = 0
    all_customers: list[Customer] = []

    for i, (first, last, email, phone) in enumerate(CUSTOMERS_B2C):
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        c = Customer(
            customer_type="B2C",
            first_name=first,
            last_name=last,
            email=email,
            phone=phone,
            is_active=True,
        )
        db.add(c)
        db.flush()
        all_customers.append(c)
        created += 1
        # Adressen für ~60 % der B2C-Kunden
        if random.random() < 0.6 and ADDRESSES:
            addr = random.choice(ADDRESSES)
            db.add(CustomerAddress(
                customer_id=c.id,
                address_type=random.choice(["main", "billing", "shipping"]),
                street=addr[0],
                house_number=addr[1],
                postal_code=addr[2],
                city=addr[3],
                country="Deutschland",
            ))

    for i, (company, email, phone) in enumerate(CUSTOMERS_B2B):
        if db.query(Customer).filter(Customer.email == email).first():
            continue
        c = Customer(
            customer_type="B2B",
            company_name=company,
            email=email,
            phone=phone,
            vat_id=f"DE{random.randint(100000000, 999999999)}" if random.random() > 0.3 else None,
            is_active=True,
        )
        db.add(c)
        db.flush()
        all_customers.append(c)
        created += 1
        # B2B meist mit Rechnungsadresse
        if random.random() < 0.8 and ADDRESSES:
            addr = random.choice(ADDRESSES)
            db.add(CustomerAddress(
                customer_id=c.id,
                address_type="billing",
                street=addr[0],
                house_number=addr[1],
                postal_code=addr[2],
                city=addr[3],
                country="Deutschland",
            ))
            if random.random() < 0.5:
                addr2 = random.choice(ADDRESSES)
                if addr2 != addr:
                    db.add(CustomerAddress(
                        customer_id=c.id,
                        address_type="shipping",
                        street=addr2[0],
                        house_number=addr2[1],
                        postal_code=addr2[2],
                        city=addr2[3],
                        country="Deutschland",
                    ))

    db.commit()

    # Deaktivierte Kunden (5 Stück) – nur beim ersten Seed
    if created > 0:
        active_list = db.query(Customer).filter(Customer.is_active == True).all()
        to_deactivate = min(5, max(0, len(active_list) - 10))
        for c in random.sample(active_list, to_deactivate):
            c.is_active = False

    # Gelöschte (DSGVO-anonymisierte) Kunden – 3 Stück simulieren
    for _ in range(3):
        c = Customer(
            customer_type="B2C",
            first_name="[Anonymisiert]",
            last_name="[Anonymisiert]",
            email=f"geloescht_{uuid.uuid4().hex[:8]}@anonymisiert.local",
            phone=None,
            vat_id=None,
            notes=None,
            is_active=False,
        )
        db.add(c)
        created += 1

    db.commit()
    print(f"Kunden: {created} neu (inkl. Adressen, deaktiviert, gelöscht)")


def seed_articles(db):
    """Artikel."""
    created = 0
    for art_nr, name, ek, vk in ARTICLES:
        if db.query(Article).filter(Article.article_number == art_nr).first():
            continue
        stock = random.randint(0, 50) if random.random() > 0.3 else random.randint(0, 5)
        db.add(Article(
            article_number=art_nr,
            name=name,
            description=name,
            purchase_price=Decimal(str(ek)),
            sales_price_b2c=Decimal(str(vk)),
            sales_price_b2b=Decimal(str(round(vk * 0.92, 2))),
            vat_rate=Decimal("19"),
            stock_quantity=stock,
            minimum_stock=random.choice([0, 0, 5, 10]),
            barcode=f"400{random.randint(1000000000, 9999999999)}" if random.random() > 0.5 else None,
        ))
        created += 1
    db.commit()
    print(f"Artikel: {created} neu")


def seed_vehicles(db):
    """Fahrzeuge (nur aktive Kunden)."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    manufacturers = db.query(Manufacturer).all()
    if not customers or not manufacturers:
        print("Keine Kunden/Hersteller – Fahrzeuge übersprungen")
        return

    existing = db.query(Vehicle).count()
    target = 30
    if existing >= target:
        print(f"Fahrzeuge: bereits {existing} vorhanden")
        return

    colors = ["Schwarz", "Weiß", "Rot", "Blau", "Grün", "Silber", "Grau", "Gelb", "Orange"]
    for i in range(target - existing):
        c = random.choice(customers)
        m = random.choice(manufacturers)
        models = db.query(VehicleModel).filter(VehicleModel.manufacturer_id == m.id).all()
        vm = random.choice(models) if models else None
        model_names = MODELS.get(m.name, [f"{m.name} Modell"])
        model_free = random.choice(model_names) if model_names else f"{m.name} Standard"

        v = Vehicle(
            customer_id=c.id,
            manufacturer_id=m.id,
            vehicle_model_id=vm.id if vm else None,
            model_name_free=model_free if not vm else None,
            category=random.choice(["quad", "motorcycle"]),
            build_year=random.randint(2015, 2024),
            vin=f"WVW{1000000000000000 + (existing + i) * 12345}",
            license_plate=f"AT-{4000 + existing + i}" if random.random() > 0.2 else None,
            mileage=random.randint(500, 45000) if random.random() > 0.1 else None,
            color=random.choice(colors),
        )
        db.add(v)
    db.commit()
    print(f"Fahrzeuge: {target - existing} neu")


def seed_maintenance_plans(db):
    """Werkverträge (Wartungspläne pro Hersteller/Modell)."""
    manufacturers = db.query(Manufacturer).all()
    if not manufacturers:
        return

    plans_data = [
        ("Kleine Inspektion", "Ölwechsel, Filter prüfen", 5000, None, 12),
        ("Große Inspektion", "Vollständige Durchsicht", 10000, None, 24),
        ("Bremsen-Service", "Bremsbeläge und Flüssigkeit", 20000, None, None),
        ("Getriebe-Service", "Getriebeöl wechseln", 15000, 500, None),
        ("Kettensatz-Wartung", "Kette spannen, ölen", 3000, 100, None),
    ]
    created = 0
    for m in manufacturers[:10]:
        models = db.query(VehicleModel).filter(VehicleModel.manufacturer_id == m.id).limit(2).all()
        for plan_name, desc, km, hrs, months in plans_data[:3]:
            vm_id = random.choice(models).id if models else None
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
            for task_name in ["Öl wechseln", "Filter prüfen", "Verschleißteile prüfen"]:
                db.add(MaintenanceTask(
                    maintenance_plan_id=p.id,
                    name=task_name,
                    sort_order=created,
                ))
            created += 1
    db.commit()
    print(f"Werkverträge (Wartungspläne): {created} neu")


def seed_appointments(db):
    """Termine in Vergangenheit und Zukunft."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not vehicles or not admin:
        print("Termine: fehlende Abhängigkeiten")
        return

    existing = db.query(Appointment).count()
    target = 25
    if existing >= target:
        print(f"Termine: bereits {existing} vorhanden")
        return

    now = datetime.now(timezone.utc)
    types_ = ["workshop", "workshop", "workshop", "test_drive"]
    statuses_past = ["completed", "completed", "cancelled"]
    statuses_future = ["planned", "confirmed", "planned"]

    for i in range(target - existing):
        c = random.choice(customers)
        v = random.choice([x for x in vehicles if x.customer_id == c.id] or vehicles)
        apt_type = random.choice(types_)
        # 50 % Vergangenheit, 50 % Zukunft
        if random.random() < 0.5:
            days = -random.randint(1, 90)
            status = random.choice(statuses_past)
        else:
            days = random.randint(1, 60)
            status = random.choice(statuses_future)

        start = (now + timedelta(days=days)).replace(hour=9 + (i % 6), minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)

        a = Appointment(
            customer_id=c.id,
            vehicle_id=v.id,
            appointment_type=apt_type,
            source="internal",
            status=status,
            title=f"{'Werkstatt' if apt_type == 'workshop' else 'Probefahrt'} – {v.license_plate or v.vin or 'Fahrzeug'}",
            starts_at=start,
            ends_at=end,
            created_by=admin.id,
        )
        db.add(a)
    db.commit()
    print(f"Termine: {target - existing} neu (Vergangenheit + Zukunft)")


def seed_workshop_orders(db):
    """Werkstattaufträge mit verschiedenen Status."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).all()
    articles = db.query(Article).filter(Article.is_active == True).all()
    appointments = db.query(Appointment).filter(Appointment.status.in_(["planned", "confirmed", "completed"])).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not vehicles or not articles or not admin:
        print("Werkstattaufträge: fehlende Abhängigkeiten")
        return

    existing = db.query(WorkshopOrder).count()
    target = 25
    if existing >= target:
        print(f"Werkstattaufträge: bereits {existing} vorhanden")
        return

    statuses = ["new", "planned", "in_progress", "completed", "invoiced", "cancelled"]
    complaints = [
        "Ölwechsel und Inspektion",
        "Bremsen quietschen",
        "Motor läuft unrund",
        "Kette muss gespannt werden",
        "Reifenwechsel",
        "Getriebeöl wechseln",
        "Zündkerzen wechseln",
    ]

    for i in range(target - existing):
        c = random.choice(customers)
        v_list = [x for x in vehicles if x.customer_id == c.id]
        v = random.choice(v_list) if v_list else random.choice(vehicles)
        apt = random.choice(appointments) if appointments and random.random() < 0.4 else None
        status = statuses[i % len(statuses)] if i < len(statuses) else random.choice(statuses)

        order = WorkshopOrder(
            customer_id=c.id,
            vehicle_id=v.id,
            appointment_id=apt.id if apt else None,
            order_number=f"WO-SEED-{2024}{5000 + existing + i}",
            status=status,
            complaint_description=random.choice(complaints),
            mileage_at_checkin=v.mileage,
            estimated_work_minutes=random.choice([60, 90, 120, 180]),
            actual_work_minutes=random.choice([45, 75, 110, 170]) if status in ("completed", "invoiced") else None,
            created_by=admin.id,
        )
        db.add(order)
        db.flush()

        # Positionen
        art = random.sample(articles, min(2, len(articles)))
        for j, a in enumerate(art):
            qty = Decimal("1") if j == 0 else Decimal(str(round(random.uniform(0.5, 3), 2)))
            price = a.sales_price_b2c
            db.add(WorkshopOrderItem(
                workshop_order_id=order.id,
                item_type="material",
                article_id=a.id,
                description=a.name,
                quantity=qty,
                unit="Stück",
                unit_price=price,
                vat_rate=Decimal("19"),
                source="manual",
            ))
        db.add(WorkshopOrderItem(
            workshop_order_id=order.id,
            item_type="labor",
            description="Arbeitszeit",
            quantity=Decimal("1.5"),
            unit="Stunde",
            unit_price=Decimal("85.00"),
            vat_rate=Decimal("19"),
            source="manual",
        ))

    db.commit()
    print(f"Werkstattaufträge: {target - existing} neu")


def seed_invoices(db):
    """Rechnungen mit verschiedenen Status."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    orders = db.query(WorkshopOrder).filter(
        WorkshopOrder.status.in_(["completed", "invoiced"])
    ).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not admin:
        print("Rechnungen: fehlende Abhängigkeiten")
        return

    existing = db.query(Invoice).count()
    target = 20
    if existing >= target:
        print(f"Rechnungen: bereits {existing} vorhanden")
        return

    statuses = ["draft", "issued", "partially_paid", "paid", "cancelled"]
    for i in range(target - existing):
        c = random.choice(customers)
        wo = random.choice(orders) if orders and random.random() < 0.6 else None
        status = statuses[i % len(statuses)]
        inv_date = date.today() - timedelta(days=random.randint(0, 90))
        due = inv_date + timedelta(days=14)

        net = Decimal(str(round(random.uniform(150, 1200), 2)))
        vat = net * Decimal("0.19")
        gross = net + vat

        inv = Invoice(
            customer_id=c.id,
            workshop_order_id=wo.id if wo else None,
            invoice_number=f"RE-SEED-{2024}{3000 + existing + i}",
            invoice_date=inv_date,
            due_date=due,
            status=status,
            net_amount=net,
            vat_amount=vat,
            gross_amount=gross,
            payment_method="Überweisung" if status == "paid" else None,
            reminder_level=random.choice([0, 0, 0, 1, 2]) if status in ("issued", "partially_paid") else 0,
            reminder_date=inv_date + timedelta(days=30) if status == "partially_paid" and random.random() > 0.5 else None,
            created_by=admin.id,
        )
        db.add(inv)
        db.flush()
        db.add(InvoiceItem(
            invoice_id=inv.id,
            description="Werkstattleistung",
            quantity=Decimal("1"),
            unit="Auftrag",
            unit_price=net,
            vat_rate=Decimal("19"),
            line_total_net=net,
        ))

    db.commit()
    print(f"Rechnungen: {target - existing} neu (versch. Status)")


def seed_documents(db):
    """Dokumente (Platzhalter-Dateien)."""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    vehicles = db.query(Vehicle).all()
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    if not customers or not admin:
        print("Dokumente: fehlende Abhängigkeiten")
        return

    upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    doc_types = [
        ("Fahrzeugschein.pdf", "application/pdf"),
        ("Kaufvertrag.pdf", "application/pdf"),
        ("Versicherungspolice.pdf", "application/pdf"),
        ("Inspektionsheft.pdf", "application/pdf"),
        ("Rechnung_Lieferant.pdf", "application/pdf"),
        ("Foto_Fahrzeug.jpg", "image/jpeg"),
        ("Zulassungsbescheinigung.pdf", "application/pdf"),
    ]

    existing = db.query(Document).count()
    target = 20
    if existing >= target:
        print(f"Dokumente: bereits {existing} vorhanden")
        return

    for i in range(target - existing):
        c = random.choice(customers)
        v = random.choice([x for x in vehicles if x.customer_id == c.id] or vehicles)
        fname, ctype = random.choice(doc_types)
        fpath = f"seed_{uuid.uuid4().hex[:8]}_{fname}"
        full_path = Path(upload_dir) / fpath
        full_path.write_text(f"Platzhalter-Dokument für Seed-Daten\nKunde: {c.id}\nFahrzeug: {v.id if v else '-'}\n", encoding="utf-8")

        db.add(Document(
            customer_id=c.id,
            vehicle_id=v.id if v else None,
            filename=fname,
            content_type=ctype,
            file_path=str(fpath),
            file_size=full_path.stat().st_size,
            created_by=admin.id,
        ))
    db.commit()
    print(f"Dokumente: {target - existing} neu")


def seed_audit_logs(db):
    """Audit Logs (verschiedene Aktionen)."""
    admin = db.query(User).filter(User.email == "admin@warevision.local").first()
    customers = db.query(Customer).limit(5).all()
    if not admin:
        print("Audit Logs: kein Admin-User")
        return

    existing = db.query(AuditLog).count()
    target = 30
    if existing >= target:
        print(f"Audit Logs: bereits {existing} vorhanden")
        return

    actions = [
        ("customer", "create", {"email": "neu@example.de"}, None),
        ("customer", "update", {"phone": "0171-9999999"}, {"phone": "0171-1234567"}),
        ("customer", "delete", None, {"email": "alt@example.de"}),
        ("vehicle", "create", {"vin": "WVW123"}, None),
        ("vehicle", "update", {"mileage": 15000}, {"mileage": 12000}),
        ("workshop_order", "create", {"order_number": "WO-20245001"}, None),
        ("invoice", "create", {"invoice_number": "RE-2024001"}, None),
        ("user", "login", None, None),
        ("settings", "update", {"company_name": "WareVision GmbH"}, {"company_name": "WareVision"}),
    ]

    for i in range(target - existing):
        act = actions[i % len(actions)]
        entity_id = random.choice(customers).id if customers and "customer" in act[1] else None
        db.add(AuditLog(
            user_id=admin.id,
            entity_type=act[0],
            entity_id=entity_id,
            action=act[1],
            old_values=act[3],
            new_values=act[2],
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            user_agent="Mozilla/5.0 (Seed-Script)",
        ))
    db.commit()
    print(f"Audit Logs: {target - existing} neu")


def main():
    db = SessionLocal()
    try:
        print("Seed startet...")
        seed_manufacturers(db)
        seed_customers(db)
        seed_articles(db)
        seed_vehicles(db)
        seed_maintenance_plans(db)
        seed_appointments(db)
        seed_workshop_orders(db)
        seed_invoices(db)
        seed_documents(db)
        seed_audit_logs(db)
        print("Seed abgeschlossen.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
