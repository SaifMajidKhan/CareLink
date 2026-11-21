from datetime import datetime, timedelta, timezone

from app.analytics.risk_engine import RiskDose, calculate_risk
from app.analytics.trend_engine import calculate_adherence_trend


def assess_adherence_risk(
    doses: list[RiskDose],
    as_of: datetime,
) -> dict:
    """
    Combine adherence risk and recent adherence trends.

    Uses the most recent 14 days of expected dose occurrences.
    A declining trend adds 15 points to the base risk score.

    This is an explainable prototype indicator,
    not a clinically validated prediction.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")

    cutoff = as_of.astimezone(timezone.utc)
    window_start = cutoff - timedelta(days=14)

    recent_doses = []

    for dose in doses:
        timestamp = dose.scheduled_for

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Dose timestamps must include a timezone")

        timestamp = timestamp.astimezone(timezone.utc)

        if window_start <= timestamp <= cutoff:
            recent_doses.append(dose)

    base_risk = calculate_risk(recent_doses)

    trend_result = calculate_adherence_trend(
        recent_doses,
        as_of=cutoff,
    )

    base_score = base_risk["risk_score"]
    trend = trend_result["trend"]

    reasons = list(base_risk["reasons"])

    if base_score is None:
        final_score = None
        final_level = "insufficient_data"
        trend_adjustment = 0

    else:
        trend_adjustment = 0

        if trend == "declining":
            trend_adjustment = 15
            reasons.append(
                "Recorded adherence declined by at least "
                "10 percentage points compared with "
                "the previous seven days"
            )

        elif trend == "improving":
            reasons.append(
                "Recorded adherence improved compared "
                "with the previous seven days"
            )

        elif trend == "stable":
            reasons.append(
                "Recorded adherence remained relatively stable"
            )

        final_score = min(
            base_score + trend_adjustment,
            100,
        )

        if final_score >= 60:
            final_level = "high"
        elif final_score >= 25:
            final_level = "medium"
        else:
            final_level = "low"

    return {
        "risk_level": final_level,
        "risk_score": final_score,
        "base_risk_score": base_score,
        "trend_adjustment": trend_adjustment,
        "confidence": base_risk["confidence"],
        "trend": trend,
        "trend_change_percentage_points": (
            trend_result["change_percentage_points"]
        ),
        "reasons": reasons,
        "metrics": base_risk["metrics"],
        "trend_details": trend_result,
        "assessment_type": "rule_based_adherence_risk",
        "clinical_prediction": False,
    }