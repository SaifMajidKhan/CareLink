from datetime import datetime, timedelta, timezone

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