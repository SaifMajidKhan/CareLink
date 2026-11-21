from datetime import date, datetime, timedelta, timezone

from app.analytics.adherence_engine import (
    DoseEventInput,
    ScheduleInput,
    calculate_adherence,
)
from app.analytics.risk_engine import RiskDose
from app.models import AdherenceStatus


def build_risk_doses(
    schedules: list[ScheduleInput],
    events: list[DoseEventInput],
    window_start: date,
    window_end: date,
    as_of: datetime,
) -> list[RiskDose]:
    """
    Convert expected schedule occurrences into risk inputs.

    Missing event = UNKNOWN, never automatically MISSED.
    Each occurrence retains its schedule ID.
    """

    # Reuse existing validation of schedules, events,
    # date windows, timezones and occurrence matching.
    calculate_adherence(
        schedules=schedules,
        events=events,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of,
    )

    cutoff = as_of.astimezone(timezone.utc)

    event_lookup = {
        (
            event.schedule_id,
            event.scheduled_for.astimezone(timezone.utc),
        ): event.status
        for event in events
    }

    doses = []

    for schedule in schedules:
        current = max(window_start, schedule.start_date)
        last = window_end

        if schedule.end_date is not None:
            last = min(last, schedule.end_date)

        deactivated = (
            schedule.deactivated_at.astimezone(timezone.utc)
            if schedule.deactivated_at is not None
            else None
        )

        while current <= last:
            valid_day = (
                not schedule.days_of_week
                or current.weekday() in schedule.days_of_week
            )

            if valid_day:
                occurrence = datetime.combine(
                    current,
                    schedule.scheduled_time,
                    tzinfo=timezone.utc,
                )

                if occurrence <= cutoff and (
                    deactivated is None
                    or occurrence < deactivated
                ):
                    status = event_lookup.get(
                        (schedule.id, occurrence),
                        AdherenceStatus.UNKNOWN,
                    )

                    doses.append(
                        RiskDose(
                            scheduled_for=occurrence,
                            status=status,
                            schedule_id=schedule.id,
                        )
                    )

            current += timedelta(days=1)

    return sorted(
        doses,
        key=lambda dose: (
            dose.scheduled_for,
            str(dose.schedule_id),
        ),
    )