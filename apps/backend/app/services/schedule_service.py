from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MedicationSchedule
from app.schemas.schedule import ScheduleCreate
from app.services.medication_service import get_patient_medication


class InvalidScheduleDatesError(Exception):
    """Schedule dates fall outside the medication dates."""


class InactiveMedicationError(Exception):
    """Cannot schedule an inactive medication."""


def create_schedule(
    db: Session,
    patient_id: UUID,
    medication_id: UUID,
    data: ScheduleCreate,
) -> MedicationSchedule | None:
    medication = get_patient_medication(
        db, patient_id, medication_id
    )

    if medication is None:
        return None

    if not medication.is_active:
        raise InactiveMedicationError()

    if data.start_date < medication.start_date:
        raise InvalidScheduleDatesError()

    if (
    medication.end_date is not None
    and data.start_date > medication.end_date
):
        raise InvalidScheduleDatesError()
    if (
        medication.end_date is not None
        and (
            data.end_date is None
            or data.end_date > medication.end_date
        )
    ):
        raise InvalidScheduleDatesError()

    schedule = MedicationSchedule(
        medication_id=medication.id,
        **data.model_dump(),
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return schedule


def list_medication_schedules(
    db: Session,
    patient_id: UUID,
    medication_id: UUID,
) -> list[MedicationSchedule] | None:
    medication = get_patient_medication(
        db, patient_id, medication_id
    )

    if medication is None:
        return None

    statement = (
        select(MedicationSchedule)
        .where(MedicationSchedule.medication_id == medication.id)
        .order_by(
            MedicationSchedule.scheduled_time,
            MedicationSchedule.id,
        )
    )

    return list(db.scalars(statement).all())