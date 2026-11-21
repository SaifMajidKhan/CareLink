from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.analytics.risk_engine import RiskDose, calculate_risk
from app.models import AdherenceStatus


def make_doses(statuses):
    start = datetime(2026, 11, 15, 8, tzinfo=timezone.utc)

    return [
        RiskDose(
            scheduled_for=start + timedelta(days=index),
            status=status,
        )
        for index, status in enumerate(statuses)
    ]


T = AdherenceStatus.TAKEN
M = AdherenceStatus.MISSED
U = AdherenceStatus.UNKNOWN
S = AdherenceStatus.SKIPPED


def test_all_taken_is_low_risk():
    result = calculate_risk(make_doses([T, T, T, T]))

    assert result["risk_level"] == "low"
    assert result["risk_score"] == 0


def test_many_missed_doses_are_high_risk():
    result = calculate_risk(make_doses([M, M, M, T]))

    assert result["risk_level"] == "high"
    assert result["risk_score"] == 80


def test_two_consecutive_misses():
    result = calculate_risk(make_doses([T, M, M, T]))

    assert result["risk_level"] == "high"
    assert result["risk_score"] == 65
    assert result["metrics"]["longest_missed_streak"] == 2


def test_unrecorded_doses_do_not_count_as_missed():
    result = calculate_risk(make_doses([T, U, U, U]))

    assert result["risk_level"] == "insufficient_data"
    assert result["metrics"]["missed"] == 0
    assert result["metrics"]["unrecorded"] == 3


def test_no_doses_returns_insufficient_data():
    result = calculate_risk([])

    assert result["risk_level"] == "insufficient_data"
    assert result["risk_score"] is None


def test_skipped_is_not_confirmed_missed():
    result = calculate_risk(make_doses([T, S, T, S]))

    assert result["risk_level"] == "low"
    assert result["metrics"]["missed"] == 0


def test_doses_sorted_before_streak_calculation():
    doses = make_doses([M, M, T, T])
    result = calculate_risk(list(reversed(doses)))

    assert result["metrics"]["longest_missed_streak"] == 2


def test_naive_timestamp_rejected():
    doses = [
        RiskDose(
            scheduled_for=datetime(2026, 11, 15, 8),
            status=T,
        )
    ]

    with pytest.raises(ValueError, match="timezone"):
        calculate_risk(doses)

def test_missed_streak_is_tracked_per_schedule():
    from datetime import datetime, timedelta, timezone

    schedule_a = UUID(
        "00000000-0000-4000-8000-000000000001"
    )
    schedule_b = UUID(
        "00000000-0000-4000-8000-000000000002"
    )

    start = datetime(
        2026, 11, 15, 8, tzinfo=timezone.utc
    )

    doses = []

    for day in range(3):
        timestamp = start + timedelta(days=day)

        doses.append(
            RiskDose(
                scheduled_for=timestamp,
                status=AdherenceStatus.MISSED,
                schedule_id=schedule_a,
            )
        )

        doses.append(
            RiskDose(
                scheduled_for=timestamp,
                status=AdherenceStatus.TAKEN,
                schedule_id=schedule_b,
            )
        )

    result = calculate_risk(doses)

    assert result["metrics"]["expected"] == 6
    assert result["metrics"]["missed"] == 3
    assert result["metrics"]["longest_missed_streak"] == 3
    assert result["risk_level"] == "high"


def test_misses_on_different_schedules_do_not_form_streak():
    from datetime import datetime, timedelta, timezone

    schedule_a = UUID(
        "00000000-0000-4000-8000-000000000001"
    )
    schedule_b = UUID(
        "00000000-0000-4000-8000-000000000002"
    )

    start = datetime(
        2026, 11, 15, 8, tzinfo=timezone.utc
    )

    doses = [
        RiskDose(
            scheduled_for=start,
            status=AdherenceStatus.MISSED,
            schedule_id=schedule_a,
        ),
        RiskDose(
            scheduled_for=start,
            status=AdherenceStatus.TAKEN,
            schedule_id=schedule_b,
        ),
        RiskDose(
            scheduled_for=start + timedelta(days=1),
            status=AdherenceStatus.TAKEN,
            schedule_id=schedule_a,
        ),
        RiskDose(
            scheduled_for=start + timedelta(days=1),
            status=AdherenceStatus.MISSED,
            schedule_id=schedule_b,
        ),
    ]

    result = calculate_risk(doses)

    assert result["metrics"]["longest_missed_streak"] == 1