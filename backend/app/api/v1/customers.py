"""Customers API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
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
router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = None,
) -> list[Customer]:
    """List customers with optional search."""
    query = db.query(Customer).filter(Customer.is_active == True)
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


@router.get("/{customer_id}/export")
def export_customer_data(
    customer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
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
