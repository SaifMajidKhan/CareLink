from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AdherenceEvent, MedicationSchedule
from app.schemas.adherence import AdherenceEventCreate


class InvalidDoseOccurrenceError(Exception):
    pass


class DuplicateDoseEventError(Exception):
    pass


class InactiveScheduleError(Exception):
    pass


def get_owned_schedule(
    db: Session,
    patient_id: UUID,
    medication_id: UUID,
    schedule_id: UUID,
) -> MedicationSchedule | None:
    from app.models import Medication

    return db.scalar(
        select(MedicationSchedule)
        .join(Medication)
        .where(
            MedicationSchedule.id == schedule_id,
            MedicationSchedule.medication_id == medication_id,
            Medication.patient_id == patient_id,
        )
    )


def create_adherence_event(
    db: Session,
    schedule: MedicationSchedule,
    patient_id: UUID,
    data: AdherenceEventCreate,
) -> AdherenceEvent:
    if not schedule.is_active or not schedule.medication.is_active:
        raise InactiveScheduleError()

    occurrence = data.scheduled_for.astimezone(timezone.utc)

    # First version: schedules are interpreted in UTC.
    if occurrence > datetime.now(timezone.utc):
        raise InvalidDoseOccurrenceError()

    if (
        occurrence.date() < schedule.start_date
        or (
            schedule.end_date is not None
            and occurrence.date() > schedule.end_date
        )
    ):
        raise InvalidDoseOccurrenceError()

    if (
        occurrence.hour != schedule.scheduled_time.hour
        or occurrence.minute != schedule.scheduled_time.minute
        or occurrence.second != schedule.scheduled_time.second
        or occurrence.microsecond != 0
    ):
        raise InvalidDoseOccurrenceError()

    if (
        schedule.days_of_week
        and occurrence.weekday() not in schedule.days_of_week
    ):
        raise InvalidDoseOccurrenceError()

    event = AdherenceEvent(
        schedule_id=schedule.id,
        recorded_by_user_id=patient_id,
        scheduled_for=occurrence,
        status=data.status,
        notes=data.notes,
    )

    db.add(event)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateDoseEventError()

    db.refresh(event)
    return event


def list_adherence_events(
    db: Session,
    schedule_id: UUID,
) -> list[AdherenceEvent]:
    return list(
        db.scalars(
            select(AdherenceEvent)
            .where(AdherenceEvent.schedule_id == schedule_id)
            .order_by(
                AdherenceEvent.scheduled_for.desc(),
                AdherenceEvent.id,
            )
        ).all()
    )