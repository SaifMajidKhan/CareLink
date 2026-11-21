from datetime import date, datetime, time, timezone
from uuid import UUID

import pytest

from app.analytics.adherence_engine import (
    DoseEventInput,
    ScheduleInput,
)
from app.analytics.occurrence_builder import build_risk_doses
from app.models import AdherenceStatus


A = UUID("00000000-0000-4000-8000-000000000001")
B = UUID("00000000-0000-4000-8000-000000000002")

START = date(2026, 11, 15)
END = date(2026, 11, 17)
AS_OF = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def schedule(schedule_id=A):
    return ScheduleInput(
        id=schedule_id,
        scheduled_time=time(8, 0),
        days_of_week=[],
        start_date=START,
    )


def event(day, status, schedule_id=A):
    return DoseEventInput(
        schedule_id=schedule_id,
        scheduled_for=datetime(
            2026, 11, day, 8, tzinfo=timezone.utc
        ),
        status=status,
    )


def build(schedules, events, as_of=AS_OF):
    return build_risk_doses(
        schedules,
        events,
        START,
        END,
        as_of,
    )


def test_unrecorded_occurrences_become_unknown():
    doses = build([schedule()], [])

    assert len(doses) == 3
    assert all(
        dose.status == AdherenceStatus.UNKNOWN
        for dose in doses
    )


def test_recorded_statuses_preserved():
    doses = build(
        [schedule()],
        [
            event(15, AdherenceStatus.TAKEN),
            event(16, AdherenceStatus.MISSED),
        ],
    )

    assert [dose.status for dose in doses] == [
        AdherenceStatus.TAKEN,
        AdherenceStatus.MISSED,
        AdherenceStatus.UNKNOWN,
    ]


def test_same_time_different_schedules_preserved():
    doses = build(
        [schedule(A), schedule(B)],
        [],
    )

    assert len(doses) == 6
    assert len([
        dose for dose in doses
        if dose.scheduled_for.date() == START
    ]) == 2
    assert {dose.schedule_id for dose in doses} == {A, B}


def test_deactivation_excludes_future_occurrences():
    item = schedule()
    item.deactivated_at = datetime(
        2026, 11, 16, 7, tzinfo=timezone.utc
    )

    doses = build([item], [])

    assert len(doses) == 1


def test_future_occurrences_excluded():
    cutoff = datetime(
        2026, 11, 16, 7, tzinfo=timezone.utc
    )

    doses = build([schedule()], [], as_of=cutoff)

    assert len(doses) == 1


def test_weekday_schedule():
    item = schedule()
    item.days_of_week = [0]  # Monday, November 16

    doses = build([item], [])

    assert len(doses) == 1
    assert doses[0].scheduled_for.date() == date(
        2026, 11, 16
    )


def test_duplicate_events_rejected():
    with pytest.raises(ValueError, match="Duplicate dose"):
        build(
            [schedule()],
            [
                event(15, AdherenceStatus.TAKEN),
                event(15, AdherenceStatus.TAKEN),
            ],
        )


def test_unknown_schedule_event_rejected():
    with pytest.raises(ValueError, match="unknown schedule"):
        build(
            [schedule(A)],
            [event(15, AdherenceStatus.TAKEN, B)],
        )


def test_invalid_date_window_rejected():
    with pytest.raises(ValueError, match="Window end"):
        build_risk_doses(
            [],
            [],
            END,
            START,
            AS_OF,
        )