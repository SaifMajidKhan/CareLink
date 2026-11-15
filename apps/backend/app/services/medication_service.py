from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medication
from app.schemas.medication import MedicationCreate, MedicationUpdate


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


def update_medication(
    db: Session,
    medication: Medication,
    data: MedicationUpdate,
) -> Medication:
    """Update a medication while preserving date consistency."""

    changes = data.model_dump(exclude_unset=True)

    # These two fields cannot be null in the database.
    for field in ("name", "dosage", "start_date"):
        if field in changes and changes[field] is None:
            raise ValueError(f"{field} cannot be null")

    new_start = changes.get("start_date", medication.start_date)
    new_end = changes.get("end_date", medication.end_date)

    if new_end is not None and new_end < new_start:
        raise InvalidMedicationDatesError()

    for field, value in changes.items():
        setattr(medication, field, value)

    db.commit()
    db.refresh(medication)

    return medication


def deactivate_medication(
    db: Session,
    medication: Medication,
) -> Medication:
    """Mark a medication as inactive without deleting it."""

    medication.is_active = False

    db.commit()
    db.refresh(medication)

    return medication