"""Passenden Wartungsplan für ein Fahrzeug finden (Hersteller, Modell, Baujahr)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.maintenance_plan import MaintenancePlan


def plan_fits_year(plan: MaintenancePlan, build_year: int | None) -> bool:
    """Baujahr-Bereich prüfen. Pläne ohne Bereich gelten für alle Baujahre.

    Ist das Baujahr des Fahrzeugs unbekannt, passen nur Pläne ohne Bereich.
    """
    if plan.build_year_from is None and plan.build_year_to is None:
        return True
    if build_year is None:
        return False
    if plan.build_year_from is not None and build_year < plan.build_year_from:
        return False
    if plan.build_year_to is not None and build_year > plan.build_year_to:
        return False
    return True


def find_plan_for_vehicle(db: Session, vehicle) -> MaintenancePlan | None:
    """Bester Plan: Modell vor Hersteller; innerhalb davon Plan mit passendem Baujahr vor Plan ohne Bereich."""
    if vehicle is None or vehicle.manufacturer_id is None:
        return None
    candidates = (
        db.query(MaintenancePlan)
        .filter(MaintenancePlan.manufacturer_id == vehicle.manufacturer_id)
        .order_by(MaintenancePlan.name)
        .all()
    )
    build_year = getattr(vehicle, "build_year", None)

    def rank(plan: MaintenancePlan) -> tuple[int, int] | None:
        if plan.vehicle_model_id is not None and plan.vehicle_model_id != vehicle.vehicle_model_id:
            return None
        if not plan_fits_year(plan, build_year):
            return None
        model_rank = 0 if plan.vehicle_model_id is not None else 1
        has_range = plan.build_year_from is not None or plan.build_year_to is not None
        return (model_rank, 0 if has_range else 1)

    ranked = [(r, p) for p in candidates if (r := rank(p)) is not None]
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
    return ranked[0][1]
