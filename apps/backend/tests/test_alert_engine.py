import pytest

from app.analytics.alert_engine import evaluate_caregiver_alert


def assessment(level, score, confidence="high", reasons=None):
    return {
        "risk_level": level,
        "risk_score": score,
        "confidence": confidence,
        "reasons": reasons or [],
    }


def test_high_risk_generates_high_alert():
    result = evaluate_caregiver_alert(
        assessment(
            "high",
            80,
            reasons=["Repeated missed doses"],
        )
    )

    assert result.should_alert is True
    assert result.severity == "high"
    assert "Repeated missed doses" in result.message


def test_medium_risk_generates_medium_alert():
    result = evaluate_caregiver_alert(
        assessment("medium", 40)
    )

    assert result.should_alert is True
    assert result.severity == "medium"


def test_low_risk_does_not_generate_alert():
    result = evaluate_caregiver_alert(
        assessment("low", 10)
    )

    assert result.should_alert is False


def test_insufficient_data_does_not_generate_alert():
    result = evaluate_caregiver_alert(
        assessment("insufficient_data", None, "low")
    )

    assert result.should_alert is False


def test_low_confidence_does_not_generate_alert():
    result = evaluate_caregiver_alert(
        assessment("high", 70, "low")
    )

    assert result.should_alert is False


def test_invalid_risk_level_rejected():
    with pytest.raises(ValueError):
        evaluate_caregiver_alert(
            assessment("critical", 90)
        )