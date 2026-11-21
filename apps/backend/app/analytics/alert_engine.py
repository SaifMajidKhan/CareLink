from dataclasses import dataclass


@dataclass(frozen=True)
class AlertDecision:
    should_alert: bool
    severity: str | None
    title: str | None
    message: str | None
    risk_score: int | None


def evaluate_caregiver_alert(assessment: dict) -> AlertDecision:
    """
    Decide whether an adherence-risk assessment
    warrants a caregiver notification.

    Prototype rules only; not clinical predictions.
    """

    level = assessment["risk_level"]
    score = assessment["risk_score"]
    confidence = assessment["confidence"]

    if level == "insufficient_data" or score is None:
        return AlertDecision(
            should_alert=False,
            severity=None,
            title=None,
            message=None,
            risk_score=None,
        )

    if level == "low":
        return AlertDecision(
            should_alert=False,
            severity=None,
            title=None,
            message=None,
            risk_score=score,
        )

    if level not in ("medium", "high"):
        raise ValueError("Unsupported risk level")

    if confidence not in ("high", "moderate"):
        return AlertDecision(
            should_alert=False,
            severity=None,
            title=None,
            message=None,
            risk_score=score,
        )

    reasons = assessment.get("reasons", [])

    if level == "high":
        title = "High medication adherence risk"
        severity = "high"
    else:
        title = "Medication adherence needs attention"
        severity = "medium"

    explanation = (
        "; ".join(reasons[:3])
        if reasons
        else "Recent medication adherence patterns need review"
    )

    return AlertDecision(
        should_alert=True,
        severity=severity,
        title=title,
        message=explanation,
        risk_score=score,
    )