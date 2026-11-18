from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.adherence_engine import (
    DoseEventInput,
    ScheduleInput,
    calculate_adherence,
)
from app.models import AdherenceEvent, Medication, MedicationSchedule


def get_patient_adherence_summary(
    db: Session,
    patient_id: UUID,
    start_date: date,
    end_date: date,
) -> dict:
    as_of = datetime.now(timezone.utc)

    # Retrieve only schedules belonging to this patient.
    # Include inactive schedules for historical analysis.
    schedules = list(
        db.scalars(
            select(MedicationSchedule)
            .join(Medication)
            .where(
                Medication.patient_id == patient_id,
                MedicationSchedule.start_date <= end_date,
                (
                    (MedicationSchedule.end_date.is_(None))
                    | (MedicationSchedule.end_date >= start_date)
                ),
            )
            .order_by(MedicationSchedule.id)
        ).all()
    )

    schedule_inputs = [
    ScheduleInput(
        id=schedule.id,
        scheduled_time=schedule.scheduled_time,
        days_of_week=schedule.days_of_week,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        deactivated_at=(
            schedule.deactivated_at.replace(tzinfo=timezone.utc)
            if (
                schedule.deactivated_at is not None
                and schedule.deactivated_at.tzinfo is None
            )
            else schedule.deactivated_at
        ),
    )
    for schedule in schedules
]

    schedule_ids = [schedule.id for schedule in schedules]

    event_inputs = []

    if schedule_ids:
        window_start = datetime.combine(
            start_date, time.min, tzinfo=timezone.utc
        )
        window_end_exclusive = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        events = list(
            db.scalars(
                select(AdherenceEvent)
                .where(
                    AdherenceEvent.schedule_id.in_(schedule_ids),
                    AdherenceEvent.scheduled_for >= window_start,
                    AdherenceEvent.scheduled_for < window_end_exclusive,
                    AdherenceEvent.scheduled_for <= as_of,
                )
            ).all()
        )

        for event in events:
            timestamp = event.scheduled_for

            # SQLite may return naive datetimes even when the
            # SQLAlchemy column is declared timezone-aware.
            # CareLink stores dose occurrences in UTC.
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            event_inputs.append(
                DoseEventInput(
                    schedule_id=event.schedule_id,
                    scheduled_for=timestamp,
                    status=event.status,
                )
            )

    result = calculate_adherence(
        schedules=schedule_inputs,
        events=event_inputs,
        window_start=start_date,
        window_end=end_date,
        as_of=as_of,
    )

    unknown_deactivation_count = sum(
        1
        for schedule in schedules
        if not schedule.is_active
        and schedule.deactivated_at is None
    )

    result["historical_accuracy_warning"] = (
        "Some inactive schedules have unknown deactivation dates. "
        "Historical adherence counts may be inaccurate."
        if unknown_deactivation_count > 0
        else None
    )

    result["unknown_deactivation_schedules"] = (
        unknown_deactivation_count
    )

    return result