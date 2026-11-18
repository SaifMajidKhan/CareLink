from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medication
from app.schemas.medication import MedicationCreate, MedicationUpdate
from datetime import datetime, timezone

def create_medication(
    db: Session,
    patient_id: UUID,
    data: MedicationCreate,
) -> Medication:
    """Create a medication belonging to a patient."""

    medication = Medication(
        patient_id=patient_id,
        **data.model_dump(),
    )

    db.add(medication)
    db.commit()
    db.refresh(medication)

    return medication


def list_patient_medications(
    db: Session,
    patient_id: UUID,
) -> list[Medication]:
    """Return medications belonging to one patient."""

    statement = (
        select(Medication)
        .where(Medication.patient_id == patient_id)
        .order_by(Medication.created_at.desc(), Medication.id)
    )

    return list(db.scalars(statement).all())


def get_patient_medication(
    db: Session,
    patient_id: UUID,
    medication_id: UUID,
) -> Medication | None:
    """Find a medication only if the patient owns it."""

    return db.scalar(
        select(Medication).where(
            Medication.id == medication_id,
            Medication.patient_id == patient_id,
        )
    )

class InvalidMedicationDatesError(Exception):
    """Medication end date cannot precede its start date."""

class MedicationScheduleConflictError(Exception):
    """Medication date changes conflict with existing schedules."""


def update_medication(
    db: Session,
    medication: Medication,
    data: MedicationUpdate,
) -> Medication:
    """Update medication without invalidating existing schedules."""

    changes = data.model_dump(exclude_unset=True)

    for field in ("name", "dosage", "start_date"):
        if field in changes and changes[field] is None:
            raise ValueError(f"{field} cannot be null")

    new_start = changes.get("start_date", medication.start_date)
    new_end = changes.get("end_date", medication.end_date)

    if new_end is not None and new_end < new_start:
        raise InvalidMedicationDatesError()

    # Check active schedules before changing medication dates.
    if "start_date" in changes or "end_date" in changes:
        for schedule in medication.schedules:
            if not schedule.is_active:
                continue

            if schedule.start_date < new_start:
                raise MedicationScheduleConflictError()

            if new_end is not None:
                if schedule.start_date > new_end:
                    raise MedicationScheduleConflictError()

                if (
                    schedule.end_date is None
                    or schedule.end_date > new_end
                ):
                    raise MedicationScheduleConflictError()

    for field, value in changes.items():
        setattr(medication, field, value)

    db.commit()
    db.refresh(medication)

    return medication


def deactivate_medication(
    db: Session,
    medication: Medication,
) -> Medication:
    """Deactivate medication and schedules with one UTC timestamp."""

    if medication.deactivated_at is None:
        medication.deactivated_at = datetime.now(timezone.utc)

    medication.is_active = False

    for schedule in medication.schedules:
        if schedule.deactivated_at is None:
            schedule.deactivated_at = medication.deactivated_at

        schedule.is_active = False

    db.commit()
    db.refresh(medication)

    return medication