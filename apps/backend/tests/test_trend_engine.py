from datetime import datetime, timedelta, timezone

from app.analytics.risk_engine import RiskDose
from app.analytics.trend_engine import calculate_adherence_trend
from app.models import AdherenceStatus


AS_OF = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)

T = AdherenceStatus.TAKEN
M = AdherenceStatus.MISSED
U = AdherenceStatus.UNKNOWN


def make_period_doses(previous, recent):
    doses = []

    for index, status in enumerate(previous):
        doses.append(
            RiskDose(
                scheduled_for=AS_OF - timedelta(
                    days=14 - index
                ),
                status=status,
            )
        )

    for index, status in enumerate(recent):
        doses.append(
            RiskDose(
                scheduled_for=AS_OF - timedelta(
                    days=7 - index
                ),
                status=status,
            )
        )

    return doses


def test_declining_adherence():
    doses = make_period_doses(
        [T, T, T, T, T, T, T],
        [T, T, M, M, M, M, M],
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["trend"] == "declining"
    assert result["change_percentage_points"] < 0


def test_improving_adherence():
    doses = make_period_doses(
        [M, M, M, M, T, T, T],
        [T, T, T, T, T, T, T],
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["trend"] == "improving"
    assert result["change_percentage_points"] > 0


def test_stable_adherence():
    doses = make_period_doses(
        [T] * 7,
        [T] * 7,
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["trend"] == "stable"
    assert result["change_percentage_points"] == 0


def test_insufficient_recorded_data():
    doses = make_period_doses(
        [T, T, T, T, T, T, T],
        [U, U, U, U, U, U, U],
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["trend"] == "insufficient_data"
    assert result["change_percentage_points"] is None


def test_unrecorded_not_counted_as_missed():
    doses = make_period_doses(
        [T] * 7,
        [T, T, T, T, U, U, U],
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["recent_7_days"]["missed"] == 0
    assert result["recent_7_days"]["unrecorded"] == 3
    assert result["trend"] == "stable"


def test_future_doses_excluded():
    doses = make_period_doses(
        [T] * 7,
        [T] * 7,
    )

    doses.append(
        RiskDose(
            scheduled_for=AS_OF + timedelta(days=1),
            status=M,
        )
    )

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["recent_7_days"]["expected"] == 7


def test_no_doses():
    result = calculate_adherence_trend([], AS_OF)

    assert result["trend"] == "insufficient_data"
    assert result["previous_7_days"]["expected"] == 0
    assert result["recent_7_days"]["expected"] == 0


def test_same_time_different_doses_preserved():
    timestamp = AS_OF - timedelta(days=1)

    doses = [
        RiskDose(timestamp, T),
        RiskDose(timestamp, M),
    ]

    result = calculate_adherence_trend(doses, AS_OF)

    assert result["recent_7_days"]["expected"] == 2
    assert result["recent_7_days"]["taken"] == 1
    assert result["recent_7_days"]["missed"] == 1