"""Test-Konfiguration und gemeinsame Fixtures.

Tests laufen gegen die echte warevision-Datenbank, aber jeder Test
wird in einer Transaktion ausgeführt, die am Ende zurückgerollt wird.
Dadurch bleibt die Datenbank sauber – kein Commit, keine Testdaten.
"""

import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Test-URL: dieselbe DB wie dev, aber nur mit Rollback-Transaktionen
_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://warevision:warevision@localhost:5432/warevision",
)

# ------------------------------------------------------------------
# Datenbank-Setup (einmalig pro Test-Session)
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped Engine auf die warevision-Datenbank."""
    engine = create_engine(_DB_URL, pool_pre_ping=True)

    # Alle Modelle registrieren (Tabellen existieren bereits)
    from app.core.database import Base
    from app.core.database import init_db as _register_models
    _register_models()
    Base.metadata.create_all(bind=engine)  # no-op wenn Tabellen existieren

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db(test_engine):
    """Jeder Test bekommt eine eigene Verbindung mit Rollback am Ende."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Rollen anlegen (minimale Voraussetzung)
    _seed_roles(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _seed_roles(db: Session) -> None:
    """Admin- und Werkstatt-Rolle einmalig in der Transaktion anlegen."""
    from app.models.role import Role
    for name, desc in [("admin", "Administrator"), ("werkstatt", "Werkstatt")]:
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name, description=desc))
    db.flush()


# ------------------------------------------------------------------
# Benutzer-Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def admin_user(db):
    """Gibt einen Admin-Benutzer zurück."""
    from app.models.role import Role
    from app.models.user import User
    from app.core.security import get_password_hash

    role = db.query(Role).filter(Role.name == "admin").first()
    user = User(
        role_id=role.id,
        first_name="Test",
        last_name="Admin",
        email="testadmin@warevision.test",
        password_hash=get_password_hash("testpass123"),
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def werkstatt_user(db):
    """Gibt einen Werkstatt-Benutzer zurück."""
    from app.models.role import Role
    from app.models.user import User
    from app.core.security import get_password_hash

    role = db.query(Role).filter(Role.name == "werkstatt").first()
    user = User(
        role_id=role.id,
        first_name="Test",
        last_name="Werkstatt",
        email="testwerkstatt@warevision.test",
        password_hash=get_password_hash("werkstattpass123"),
    )
    db.add(user)
    db.flush()
    return user


# ------------------------------------------------------------------
# HTTP-Client-Fixture
# ------------------------------------------------------------------

@pytest.fixture()
def client(db):
    """TestClient mit überschriebenem DB-Dependency (kein Rate-Limit)."""
    from app.main import app
    from app.core.database import get_db
    from app.core.limiter import limiter

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Rate-Limiting in Tests deaktivieren
    limiter._storage = None  # type: ignore[attr-defined]

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(client, admin_user):
    """TestClient mit Admin-JWT-Token."""
    from app.core.security import create_access_token

    token = create_access_token(str(admin_user.id))
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def werkstatt_client(client, werkstatt_user):
    """TestClient mit Werkstatt-JWT-Token."""
    from app.core.security import create_access_token

    token = create_access_token(str(werkstatt_user.id))
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ------------------------------------------------------------------
# Daten-Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def sample_manufacturer(db):
    """Testhersteller."""
    from app.models.manufacturer import Manufacturer

    m = Manufacturer(name="Testmarke")
    db.add(m)
    db.flush()
    return m


@pytest.fixture()
def sample_vehicle(db, sample_customer, sample_manufacturer):
    """Testfahrzeug für sample_customer."""
    from app.models.vehicle import Vehicle

    v = Vehicle(
        customer_id=sample_customer.id,
        manufacturer_id=sample_manufacturer.id,
        category="quad",
    )
    db.add(v)
    db.flush()
    return v


@pytest.fixture()
def sample_customer(db):
    """Einfacher B2C-Testkunde."""
    from app.models.customer import Customer

    c = Customer(
        customer_type="B2C",
        first_name="Max",
        last_name="Mustermann",
        email="max.mustermann@test.de",
        phone="0123456789",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture()
def sample_invoice(db, sample_customer, admin_user):
    """Ausgestellte Rechnung mit einer Position."""
    from app.models.invoice import Invoice, InvoiceItem

    inv = Invoice(
        customer_id=sample_customer.id,
        invoice_number="RE-TEST-0001",
        invoice_date=date(2026, 1, 15),
        due_date=date(2026, 1, 29),
        status="issued",
        currency="EUR",
        net_amount=Decimal("100.00"),
        vat_amount=Decimal("19.00"),
        gross_amount=Decimal("119.00"),
        created_by=admin_user.id,
    )
    db.add(inv)
    db.flush()
    item = InvoiceItem(
        invoice_id=inv.id,
        description="Testleistung",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
        vat_rate=Decimal("19.00"),
        line_total_net=Decimal("100.00"),
    )
    db.add(item)
    db.flush()
    return inv
