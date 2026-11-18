from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from app.models import AdherenceStatus


@dataclass
class ScheduleInput:
    id: UUID
    scheduled_time: time
    days_of_week: list[int]
    start_date: date
    end_date: date | None = None
    deactivated_at: datetime | None = None


@dataclass
class DoseEventInput:
    schedule_id: UUID
    scheduled_for: datetime
    status: AdherenceStatus


def calculate_adherence(
    schedules: list[ScheduleInput],
    events: list[DoseEventInput],
    window_start: date,
    window_end: date,
    as_of: datetime,
) -> dict:
    """
    Calculate schedule-aware adherence.

    Assumptions:
    - Schedule times are UTC.
    - Empty days_of_week means every day.
    - Future occurrences are excluded.
    - Unrecorded and missed doses are different.
    - Window length cannot exceed 90 calendar days.
    """

    if window_end < window_start:
        raise ValueError("Window end cannot precede window start")

    if (window_end - window_start).days >= 90:
        raise ValueError("Window cannot exceed 90 days")

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")

    cutoff = as_of.astimezone(timezone.utc)

    schedule_ids = [schedule.id for schedule in schedules]

    if len(schedule_ids) != len(set(schedule_ids)):
        raise ValueError("Duplicate schedule IDs")

    valid_schedule_ids = set(schedule_ids)
    event_lookup = {}

    for event in events:
        if (
            event.scheduled_for.tzinfo is None
            or event.scheduled_for.utcoffset() is None
        ):
            raise ValueError("Event timestamps must include a timezone")

        if event.schedule_id not in valid_schedule_ids:
            raise ValueError("Event references an unknown schedule")

        occurrence = event.scheduled_for.astimezone(timezone.utc)
        key = (event.schedule_id, occurrence)

        if key in event_lookup:
            raise ValueError("Duplicate dose occurrence in input")

        event_lookup[key] = event.status

    counts = {
        "expected": 0,
        "taken": 0,
        "missed": 0,
        "skipped": 0,
        "unrecorded": 0,
    }

    matched_events = set()

    for schedule in schedules:
        if (
            schedule.end_date is not None
            and schedule.end_date < schedule.start_date
        ):
            raise ValueError("Invalid schedule dates")

        if any(day not in range(7) for day in schedule.days_of_week):
            raise ValueError("Invalid weekday")

        if len(schedule.days_of_week) != len(set(schedule.days_of_week)):
            raise ValueError("Duplicate weekdays")

        if schedule.scheduled_time.tzinfo is not None:
            raise ValueError("Schedule time must be timezone-naive")

        current_date = max(window_start, schedule.start_date)
        last_date = window_end

        if schedule.end_date is not None:
            last_date = min(last_date, schedule.end_date)

        while current_date <= last_date:
            valid_weekday = (
                not schedule.days_of_week
                or current_date.weekday() in schedule.days_of_week
            )

            if valid_weekday:
                occurrence = datetime.combine(
                    current_date,
                    schedule.scheduled_time,
                    tzinfo=timezone.utc,
                )

                if occurrence <= cutoff:
                    if schedule.deactivated_at is not None:
                        deactivated_at = schedule.deactivated_at

                        if (
                            deactivated_at.tzinfo is None
                            or deactivated_at.utcoffset() is None
                        ):
                            raise ValueError(
                                "Deactivation timestamp must include a timezone"
                            )

                        if occurrence >= deactivated_at.astimezone(timezone.utc):
                            current_date += timedelta(days=1)
                            continue

                    counts["expected"] += 1

                    key = (schedule.id, occurrence)
                    event_status = event_lookup.get(key)

                    if key in event_lookup:
                        matched_events.add(key)

                    if event_status == AdherenceStatus.TAKEN:
                        counts["taken"] += 1
                    elif event_status == AdherenceStatus.MISSED:
                        counts["missed"] += 1
                    elif event_status == AdherenceStatus.SKIPPED:
                        counts["skipped"] += 1
                    else:
                        counts["unrecorded"] += 1

            current_date += timedelta(days=1)

    if set(event_lookup) != matched_events:
        raise ValueError(
            "One or more events do not match expected occurrences"
        )

    expected = counts["expected"]

    adherence_rate = (
        round(counts["taken"] / expected * 100, 2)
        if expected > 0
        else None
    )

    return {
        **counts,
        "adherence_rate": adherence_rate,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }