from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.risk_assessment import assess_adherence_risk
from app.analytics.risk_engine import RiskDose
from app.models import AdherenceStatus


AS_OF = datetime(
    2026, 11, 21, 12, tzinfo=timezone.utc
)

T = AdherenceStatus.TAKEN
M = AdherenceStatus.MISSED
U = AdherenceStatus.UNKNOWN


def make_doses(previous, recent):
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


def test_all_taken_is_low_risk():
    result = assess_adherence_risk(
        make_doses([T] * 7, [T] * 7),
        AS_OF,
    )

    assert result["risk_level"] == "low"
    assert result["risk_score"] == 0
    assert result["trend"] == "stable"


def test_declining_trend_increases_risk():
    result = assess_adherence_risk(
        make_doses(
            [T] * 7,
            [T, T, T, T, T, M, M],
        ),
        AS_OF,
    )

    assert result["trend"] == "declining"
    assert result["trend_adjustment"] == 15
    assert result["risk_score"] == (
        result["base_risk_score"] + 15
    )


def test_improving_trend_does_not_add_risk():
    result = assess_adherence_risk(
        make_doses(
            [M, M, M, T, T, T, T],
            [T] * 7,
        ),
        AS_OF,
    )

    assert result["trend"] == "improving"
    assert result["trend_adjustment"] == 0


def test_unrecorded_data_not_automatically_high_risk():
    result = assess_adherence_risk(
        make_doses(
            [T] * 7,
            [U] * 7,
        ),
        AS_OF,
    )

    assert result["trend"] == "insufficient_data"
    assert result["metrics"]["missed"] == 0
    assert result["risk_level"] != "high"


def test_empty_doses():
    result = assess_adherence_risk([], AS_OF)

    assert result["risk_level"] == "insufficient_data"
    assert result["risk_score"] is None


def test_future_doses_are_excluded():
    doses = make_doses([T] * 7, [T] * 7)

    doses.append(
        RiskDose(
            scheduled_for=AS_OF + timedelta(days=1),
            status=M,
        )
    )

    result = assess_adherence_risk(doses, AS_OF)

    assert result["metrics"]["expected"] == 14
    assert result["metrics"]["missed"] == 0


def test_naive_as_of_rejected():
    with pytest.raises(ValueError, match="timezone"):
        assess_adherence_risk(
            [],
            datetime(2026, 11, 21, 12),
        )


def test_naive_dose_timestamp_rejected():
    doses = [
        RiskDose(
            scheduled_for=datetime(2026, 11, 20, 8),
            status=T,
        )
    ]

    with pytest.raises(ValueError, match="timezone"):
        assess_adherence_risk(doses, AS_OF)