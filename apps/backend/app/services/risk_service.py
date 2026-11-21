from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.adherence_engine import (
    DoseEventInput,
    ScheduleInput,
)
from app.analytics.occurrence_builder import build_risk_doses
from app.analytics.risk_assessment import assess_adherence_risk
from app.models import (
    AdherenceEvent,
    Medication,
    MedicationSchedule,
)


def to_utc(value: datetime) -> datetime:
    """
    Normalize stored timestamps to UTC.

    SQLite may return naive timestamps in tests.
    CareLink currently interprets stored dose times as UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def get_patient_risk_assessment(
    db: Session,
    patient_id: UUID,
    as_of: datetime | None = None,
) -> dict:
    """
    Generate a patient-scoped adherence-risk assessment
    using medication schedules and recorded dose events.
    """

    if as_of is None:
        as_of = datetime.now(timezone.utc)

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Assessment time must include a timezone")

    as_of = as_of.astimezone(timezone.utc)

    # Exact rolling 14-day assessment window.
    window_start = as_of - timedelta(days=14)

    # Query from midnight on the first calendar day.
    # This allows the occurrence builder to validate
    # events before the precise rolling cutoff.
    query_start = datetime.combine(
        window_start.date(),
        time.min,
        tzinfo=timezone.utc,
    )

    # Load schedules belonging only to this patient.
    # Inactive schedules remain available for history.
    schedules = list(
        db.scalars(
            select(MedicationSchedule)
            .join(Medication)
            .where(
                Medication.patient_id == patient_id,
                MedicationSchedule.start_date <= as_of.date(),
                (
                    MedicationSchedule.end_date.is_(None)
                    | (
                        MedicationSchedule.end_date
                        >= window_start.date()
                    )
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
                to_utc(schedule.deactivated_at)
                if schedule.deactivated_at is not None
                else None
            ),
        )
        for schedule in schedules
    ]

    schedule_ids = [
        schedule.id
        for schedule in schedules
    ]

    event_inputs = []

    if schedule_ids:
        events = list(
            db.scalars(
                select(AdherenceEvent)
                .where(
                    AdherenceEvent.schedule_id.in_(schedule_ids),
                    AdherenceEvent.scheduled_for >= query_start,
                    AdherenceEvent.scheduled_for <= as_of,
                )
            ).all()
        )

        event_inputs = [
            DoseEventInput(
                schedule_id=event.schedule_id,
                scheduled_for=to_utc(event.scheduled_for),
                status=event.status,
            )
            for event in events
        ]

    # Convert medication schedules and recorded events
    # into expected dose occurrences.
    doses = build_risk_doses(
        schedules=schedule_inputs,
        events=event_inputs,
        window_start=window_start.date(),
        window_end=as_of.date(),
        as_of=as_of,
    )

    # Apply the exact rolling 14-day timestamp boundary.
    doses = [
        dose
        for dose in doses
        if window_start <= dose.scheduled_for <= as_of
    ]

    # Run the combined risk and trend assessment.
    assessment = assess_adherence_risk(
        doses=doses,
        as_of=as_of,
    )

    # Identify legacy inactive schedules with missing
    # deactivation timestamps.
    unknown_deactivation_count = sum(
        1
        for schedule in schedules
        if not schedule.is_active
        and schedule.deactivated_at is None
    )

    assessment["assessment_time"] = as_of.isoformat()
    assessment["window_start"] = window_start.isoformat()
    assessment["window_end"] = as_of.isoformat()

    assessment["unknown_deactivation_schedules"] = (
        unknown_deactivation_count
    )

    assessment["historical_accuracy_warning"] = (
        "Some inactive schedules have unknown deactivation "
        "dates. Historical risk calculations may be inaccurate."
        if unknown_deactivation_count > 0
        else None
    )

    return assessment