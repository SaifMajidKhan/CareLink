from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medication
from app.schemas.medication import MedicationCreate


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