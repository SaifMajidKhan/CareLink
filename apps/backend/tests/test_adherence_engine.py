from datetime import date, datetime, time, timezone
from uuid import UUID

import pytest

from app.analytics.adherence_engine import (
    DoseEventInput,
    ScheduleInput,
    calculate_adherence,
)
from app.models import AdherenceStatus


SCHEDULE_ID = UUID("00000000-0000-4000-8000-000000000001")
SECOND_SCHEDULE_ID = UUID("00000000-0000-4000-8000-000000000002")


def daily_schedule(schedule_id=SCHEDULE_ID):
    return ScheduleInput(
        id=schedule_id,
        scheduled_time=time(8, 0),
        days_of_week=[],
        start_date=date(2026, 11, 15),
    )


def event(day, status, schedule_id=SCHEDULE_ID):
    return DoseEventInput(
        schedule_id=schedule_id,
        scheduled_for=datetime(
            2026, 11, day, 8, 0, tzinfo=timezone.utc
        ),
        status=status,
    )


def calculate(schedules, events, end_day=17):
    return calculate_adherence(
        schedules=schedules,
        events=events,
        window_start=date(2026, 11, 15),
        window_end=date(2026, 11, end_day),
        as_of=datetime(
            2026, 11, 17, 12, 0, tzinfo=timezone.utc
        ),
    )


def test_all_doses_taken():
    result = calculate(
        [daily_schedule()],
        [
            event(15, AdherenceStatus.TAKEN),
            event(16, AdherenceStatus.TAKEN),
            event(17, AdherenceStatus.TAKEN),
        ],
    )

    assert result["expected"] == 3
    assert result["taken"] == 3
    assert result["adherence_rate"] == 100.0


def test_mixed_adherence_statuses():
    result = calculate(
        [daily_schedule()],
        [
            event(15, AdherenceStatus.TAKEN),
            event(16, AdherenceStatus.MISSED),
        ],
    )

    assert result["expected"] == 3
    assert result["taken"] == 1
    assert result["missed"] == 1
    assert result["unrecorded"] == 1
    assert result["adherence_rate"] == 33.33


def test_skipped_dose_counted_separately():
    result = calculate(
        [daily_schedule()],
        [event(15, AdherenceStatus.SKIPPED)],
    )

    assert result["skipped"] == 1
    assert result["missed"] == 0
    assert result["unrecorded"] == 2


def test_future_doses_excluded():
    result = calculate(
        [daily_schedule()],
        [],
        end_day=20,
    )

    assert result["expected"] == 3


def test_weekday_schedule():
    monday_only = ScheduleInput(
        id=SCHEDULE_ID,
        scheduled_time=time(8, 0),
        days_of_week=[0],
        start_date=date(2026, 11, 15),
    )

    result = calculate(
        [monday_only],
        [event(16, AdherenceStatus.TAKEN)],
    )

    assert result["expected"] == 1
    assert result["taken"] == 1


def test_no_expected_doses():
    result = calculate([], [])

    assert result["expected"] == 0
    assert result["adherence_rate"] is None


def test_invalid_window_rejected():
    with pytest.raises(ValueError):
        calculate_adherence(
            schedules=[],
            events=[],
            window_start=date(2026, 11, 20),
            window_end=date(2026, 11, 15),
            as_of=datetime.now(timezone.utc),
        )


def test_window_over_90_days_rejected():
    with pytest.raises(ValueError):
        calculate_adherence(
            schedules=[],
            events=[],
            window_start=date(2026, 1, 1),
            window_end=date(2026, 5, 1),
            as_of=datetime.now(timezone.utc),
        )


def test_two_schedules_at_same_time_count_separately():
    result = calculate(
        [
            daily_schedule(SCHEDULE_ID),
            daily_schedule(SECOND_SCHEDULE_ID),
        ],
        [
            event(15, AdherenceStatus.TAKEN, SCHEDULE_ID),
            event(15, AdherenceStatus.MISSED, SECOND_SCHEDULE_ID),
        ],
    )

    assert result["expected"] == 6
    assert result["taken"] == 1
    assert result["missed"] == 1
    assert result["unrecorded"] == 4
    assert result["adherence_rate"] == 16.67


def test_events_match_the_correct_schedule():
    result = calculate(
        [
            daily_schedule(SCHEDULE_ID),
            daily_schedule(SECOND_SCHEDULE_ID),
        ],
        [
            event(15, AdherenceStatus.TAKEN, SECOND_SCHEDULE_ID),
        ],
    )

    assert result["expected"] == 6
    assert result["taken"] == 1
    assert result["unrecorded"] == 5


def test_duplicate_event_rejected():
    with pytest.raises(ValueError, match="Duplicate dose"):
        calculate(
            [daily_schedule()],
            [
                event(15, AdherenceStatus.TAKEN),
                event(15, AdherenceStatus.TAKEN),
            ],
        )


def test_unknown_schedule_event_rejected():
    with pytest.raises(ValueError, match="unknown schedule"):
        calculate(
            [daily_schedule()],
            [
                event(
                    15,
                    AdherenceStatus.TAKEN,
                    SECOND_SCHEDULE_ID,
                )
            ],
        )


def test_duplicate_schedule_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate schedule"):
        calculate(
            [
                daily_schedule(),
                daily_schedule(),
            ],
            [],
        )


def test_event_on_unscheduled_day_rejected():
    monday_only = ScheduleInput(
        id=SCHEDULE_ID,
        scheduled_time=time(8, 0),
        days_of_week=[0],
        start_date=date(2026, 11, 15),
    )

    with pytest.raises(ValueError, match="do not match"):
        calculate(
            [monday_only],
            [event(15, AdherenceStatus.TAKEN)],
        )


def test_timezone_offset_normalized():
    event_with_offset = DoseEventInput(
        schedule_id=SCHEDULE_ID,
        scheduled_for=datetime.fromisoformat(
            "2026-11-15T13:00:00+05:00"
        ),
        status=AdherenceStatus.TAKEN,
    )

    result = calculate(
        [daily_schedule()],
        [event_with_offset],
    )

    assert result["taken"] == 1


def test_naive_event_timestamp_rejected():
    invalid_event = DoseEventInput(
        schedule_id=SCHEDULE_ID,
        scheduled_for=datetime(2026, 11, 15, 8, 0),
        status=AdherenceStatus.TAKEN,
    )

    with pytest.raises(ValueError, match="timezone"):
        calculate(
            [daily_schedule()],
            [invalid_event],
        )

def test_deactivation_excludes_later_doses():
    schedule = daily_schedule()

    schedule.deactivated_at = datetime(
        2026, 11, 16, 7, 0, tzinfo=timezone.utc
    )

    result = calculate([schedule], [])

    assert result["expected"] == 1
    assert result["unrecorded"] == 1


def test_deactivation_after_dose_keeps_that_dose():
    schedule = daily_schedule()

    schedule.deactivated_at = datetime(
        2026, 11, 16, 10, 0, tzinfo=timezone.utc
    )

    result = calculate([schedule], [])

    assert result["expected"] == 2


def test_naive_deactivation_timestamp_rejected():
    schedule = daily_schedule()

    schedule.deactivated_at = datetime(
        2026, 11, 16, 10, 0
    )

    with pytest.raises(ValueError, match="timezone"):
        calculate([schedule], [])