"""Customers API."""

import base64
import uuid as uuid_lib
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, module_guard, require_right
from app.core.database import get_db
from app.models.customer import Customer, CustomerAddress
from app.models.user import User
from app.services.audit import log_audit
from app.schemas.customer import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    CustomerAddressCreate,
    CustomerAddressRead,
)
router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(module_guard("customers"))])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = None,
    include_inactive: bool = Query(False, description="Deaktivierte/gelöschte Kunden anzeigen"),
) -> list[Customer]:
    """List customers with optional search."""
    query = db.query(Customer)
    if not include_inactive:
        query = query.filter(Customer.is_active == True)
    if search:
        query = query.filter(
            Customer.company_name.ilike(f"%{search}%")
            | Customer.first_name.ilike(f"%{search}%")
            | Customer.last_name.ilike(f"%{search}%")
            | Customer.email.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Customer:
    """Create customer with duplicate check."""
    # Dublettenprüfung
    if payload.email:
        existing = db.query(Customer).filter(Customer.email == payload.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kunde mit dieser E-Mail existiert bereits",
            )
    if payload.phone:
        existing = db.query(Customer).filter(Customer.phone == payload.phone).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kunde mit dieser Telefonnummer existiert bereits",
            )

    customer = Customer(
        customer_type=payload.customer_type,
        company_name=payload.company_name,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        vat_id=payload.vat_id,
        notes=payload.notes,
    )
    db.add(customer)
    db.flush()
    log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer.id, action="create", new_values={"email": customer.email, "company_name": customer.company_name})
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Customer:
    """Get customer by ID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kunde nicht gefunden",
        )
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Customer:
    """Update customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kunde nicht gefunden",
        )
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        duplicate = (
            db.query(Customer)
            .filter(Customer.email == data["email"], Customer.id != customer_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ein anderer Kunde mit dieser E-Mail-Adresse existiert bereits",
            )
    old_vals = {k: str(getattr(customer, k)) for k in data.keys() if hasattr(customer, k)}
    for key, value in data.items():
        setattr(customer, key, value)
    log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer_id, action="update", old_values=old_vals, new_values=data)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Soft delete customer (deactivate)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kunde nicht gefunden",
        )
    customer.is_active = False
    log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer_id, action="delete", old_values={"email": customer.email, "company_name": customer.company_name})
    db.commit()


@router.get("/{customer_id}/addresses", response_model=list[CustomerAddressRead])
def list_customer_addresses(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CustomerAddress]:
    """List customer addresses."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")
    return list(customer.addresses)


@router.post("/{customer_id}/addresses", response_model=CustomerAddressRead, status_code=status.HTTP_201_CREATED)
def create_customer_address(
    customer_id: UUID,
    payload: CustomerAddressCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CustomerAddress:
    """Add address to customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")
    addr = CustomerAddress(
        customer_id=customer_id,
        address_type=payload.address_type,
        street=payload.street,
        house_number=payload.house_number,
        postal_code=payload.postal_code,
        city=payload.city,
        country=payload.country,
    )
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/{customer_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_address(
    customer_id: UUID,
    address_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove address from customer."""
    addr = (
        db.query(CustomerAddress)
        .filter(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id,
        )
        .first()
    )
    if not addr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adresse nicht gefunden")
    db.delete(addr)
    db.commit()


@router.post("/{customer_id}/dsgvo-delete")
def dsgvo_delete_customer(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("dsgvo_delete"))],
) -> dict:
    """DSGVO Art. 17: Recht auf Löschung. Anonymisiert bei Rechnungen (GoBD), sonst endgültige Löschung."""
    from app.models.invoice import Invoice
    from app.models.workshop_order import WorkshopOrder
    from app.models.vehicle import Vehicle
    from app.models.appointment import Appointment

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")

    has_invoices = db.query(Invoice).filter(Invoice.customer_id == customer_id).first() is not None
    has_orders = db.query(WorkshopOrder).filter(WorkshopOrder.customer_id == customer_id).first() is not None

    if has_invoices or has_orders:
        customer.company_name = "[Anonymisiert]"
        customer.first_name = "[Anonymisiert]"
        customer.last_name = "[Anonymisiert]"
        customer.email = f"geloescht_{customer_id.hex[:8]}@anonymisiert.local"
        customer.phone = None
        customer.vat_id = None
        customer.notes = None
        customer.is_active = False
        for addr in customer.addresses:
            addr.street = "[Anonymisiert]"
            addr.house_number = None
            addr.postal_code = "00000"
            addr.city = "[Anonymisiert]"
        # DSGVO: Kennzeichen und VIN der Fahrzeuge anonymisieren (personenbezogene Daten)
        for vehicle in db.query(Vehicle).filter(Vehicle.customer_id == customer_id).all():
            vehicle.license_plate = "[Anonymisiert]"
            vehicle.vin = None
        # DSGVO: Personenbezogene Daten aus Terminen entfernen
        for apt in db.query(Appointment).filter(Appointment.customer_id == customer_id).all():
            apt.external_booking_id = None
            apt.title = None
            apt.description = None
        # DSGVO: Fotos zu den Aufträgen (zeigen oft Kennzeichen/FIN) löschen – sie sind keine Buchungsbelege
        from app.models.workshop_order_photo import WorkshopOrderPhoto
        photo_paths = []
        order_ids = [o.id for o in db.query(WorkshopOrder.id).filter(WorkshopOrder.customer_id == customer_id).all()]
        if order_ids:
            for photo in db.query(WorkshopOrderPhoto).filter(WorkshopOrderPhoto.workshop_order_id.in_(order_ids)).all():
                photo_paths.append(photo.file_path)
                db.delete(photo)
        log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer_id, action="dsgvo_anonymize",
                  new_values={"deleted_photos": len(photo_paths)} if photo_paths else None)
        db.commit()
        import os
        for path in photo_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        return {"action": "anonymized", "reason": "Rechnungen oder Aufträge vorhanden (GoBD)"}
    else:
        for apt in db.query(Appointment).filter(Appointment.customer_id == customer_id).all():
            apt.customer_id = None
            apt.vehicle_id = None
            apt.external_booking_id = None
            apt.title = None
            apt.description = None
        log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer_id, action="dsgvo_delete", old_values={"email": customer.email})
        db.delete(customer)
        db.commit()
        return {"action": "deleted"}


@router.get("/{customer_id}/dsgvo-consent-pdf")
def get_dsgvo_consent_pdf(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """DSGVO-Einwilligungs-PDF fuer einen Kunden generieren (zum Ausdrucken und Unterschreiben)."""
    from app.services.pdf import generate_dsgvo_consent_pdf

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")

    pdf_bytes = generate_dsgvo_consent_pdf(db, customer)
    name_slug = (customer.last_name or customer.company_name or str(customer_id))[:30].replace(" ", "_")
    filename = f"DSGVO_Einwilligung_{name_slug}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{customer_id}/dsgvo-sign")
def dsgvo_sign_and_save(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    signature_data_url: str = Body(..., embed=True),
) -> dict:
    """Unterschrift entgegennehmen, ins DSGVO-PDF einbetten und bei Kundendokumenten speichern."""
    from app.services.pdf import generate_dsgvo_consent_pdf
    from app.models.document import Document
    from app.core.config import get_settings

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")

    # Base64-PNG aus Data-URL extrahieren
    if "," not in signature_data_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Unterschrift")
    sig_bytes = base64.b64decode(signature_data_url.split(",", 1)[1])

    # PDF mit Unterschrift generieren
    pdf_bytes = generate_dsgvo_consent_pdf(db, customer, signature_bytes=sig_bytes)

    # In Uploads-Verzeichnis speichern
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"DSGVO_{uuid_lib.uuid4().hex}.pdf"
    file_path = upload_dir / file_name
    file_path.write_bytes(pdf_bytes)

    # Dokument in DB anlegen
    name_slug = (customer.last_name or customer.company_name or str(customer_id))[:30].replace(" ", "_")
    doc = Document(
        customer_id=customer_id,
        filename=f"DSGVO_Einwilligung_{name_slug}_unterschrieben.pdf",
        content_type="application/pdf",
        file_path=str(file_path),
        file_size=len(pdf_bytes),
        created_by=current_user.id,
    )
    db.add(doc)
    log_audit(db, user_id=current_user.id, entity_type="customer", entity_id=customer_id, action="dsgvo_sign")
    db.commit()
    db.refresh(doc)

    return {"document_id": str(doc.id), "filename": doc.filename}


@router.get("/{customer_id}/export")
def export_customer_data(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("dsgvo_export"))],
) -> dict:
    """DSGVO: Export all customer data as JSON (admin only)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kunde nicht gefunden")

    from app.models.vehicle import Vehicle
    from app.models.workshop_order import WorkshopOrder
    from app.models.invoice import Invoice
    from app.models.appointment import Appointment

    addresses = [{"address_type": a.address_type, "street": a.street, "house_number": a.house_number, "postal_code": a.postal_code, "city": a.city, "country": a.country} for a in customer.addresses]
    vehicles = db.query(Vehicle).filter(Vehicle.customer_id == customer_id).all()
    vehicle_data = [{"license_plate": v.license_plate, "vin": v.vin, "build_year": v.build_year, "mileage": v.mileage} for v in vehicles]
    orders = db.query(WorkshopOrder).filter(WorkshopOrder.customer_id == customer_id).all()
    order_data = [{"order_number": o.order_number, "status": o.status, "created_at": str(o.created_at)} for o in orders]
    invoices = db.query(Invoice).filter(Invoice.customer_id == customer_id).all()
    invoice_data = [{"invoice_number": i.invoice_number, "status": i.status, "gross_amount": float(i.gross_amount)} for i in invoices]
    appointments = db.query(Appointment).filter(Appointment.customer_id == customer_id).all()
    appointment_data = [{"starts_at": str(a.starts_at), "appointment_type": a.appointment_type} for a in appointments]

    return {
        "exported_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "customer": {
            "customer_type": customer.customer_type,
            "company_name": customer.company_name,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone,
            "vat_id": customer.vat_id,
            "notes": customer.notes,
        },
        "addresses": addresses,
        "vehicles": vehicle_data,
        "workshop_orders": order_data,
        "invoices": invoice_data,
        "appointments": appointment_data,
    }
