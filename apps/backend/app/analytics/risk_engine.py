from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import AdherenceStatus


@dataclass(frozen=True)
class RiskDose:
    scheduled_for: datetime
    status: AdherenceStatus


def calculate_risk(doses: list[RiskDose]) -> dict:
    """
    Explainable operational adherence-risk score.

    Doses must be supplied in chronological order after sorting.
    This is a rule-based indicator, not a clinical prediction.
    """

    ordered = sorted(doses, key=lambda dose: dose.scheduled_for)

    for dose in ordered:
        if dose.scheduled_for.tzinfo is None:
            raise ValueError("Dose timestamps must include a timezone")

    total = len(ordered)

    if total == 0:
        return {
            "risk_level": "insufficient_data",
            "risk_score": None,
            "confidence": "none",
            "reasons": ["No expected doses available"],
            "metrics": {
                "expected": 0,
                "recorded": 0,
                "missed": 0,
                "unrecorded": 0,
                "longest_missed_streak": 0,
            },
        }

    taken = sum(
        dose.status == AdherenceStatus.TAKEN
        for dose in ordered
    )
    missed = sum(
        dose.status == AdherenceStatus.MISSED
        for dose in ordered
    )
    skipped = sum(
        dose.status == AdherenceStatus.SKIPPED
        for dose in ordered
    )
    unrecorded = sum(
        dose.status == AdherenceStatus.UNKNOWN
        for dose in ordered
    )

    recorded = taken + missed + skipped
    coverage = recorded / total

    streak = 0
    longest_streak = 0

    for dose in ordered:
        if dose.status == AdherenceStatus.MISSED:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    metrics = {
        "expected": total,
        "recorded": recorded,
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
        "unrecorded": unrecorded,
        "recording_coverage": round(coverage * 100, 2),
        "longest_missed_streak": longest_streak,
    }

    # Do not classify patients when evidence is too limited.
    if total < 3 or coverage < 0.5:
        return {
            "risk_level": "insufficient_data",
            "risk_score": None,
            "confidence": "low",
            "reasons": [
                "Insufficient recorded dose information"
            ],
            "metrics": metrics,
        }

    # Explicitly confirmed misses contribute to the risk score.
    missed_rate = missed / total

    score = 0
    reasons = []

    if missed_rate >= 0.5:
        score += 50
        reasons.append("At least half of expected doses were missed")
    elif missed_rate >= 0.25:
        score += 25
        reasons.append("At least one quarter of doses were missed")

    if longest_streak >= 3:
        score += 30
        reasons.append("Three or more consecutive missed doses")
    elif longest_streak >= 2:
        score += 15
        reasons.append("Two consecutive missed doses")

    if coverage < 0.8:
        score += 10
        reasons.append("Some dose records are incomplete")

    score = min(score, 100)

    if score >= 60:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"

    if not reasons:
        reasons.append("No significant missed-dose pattern detected")

    return {
        "risk_level": level,
        "risk_score": score,
        "confidence": "high" if coverage >= 0.8 else "moderate",
        "reasons": reasons,
        "metrics": metrics,
    }