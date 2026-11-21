from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models import AdherenceStatus


@dataclass(frozen=True)
class RiskDose:
    scheduled_for: datetime
    status: AdherenceStatus
    schedule_id: UUID | None = None


def calculate_risk(doses: list[RiskDose]) -> dict:
    """
    Calculate explainable medication adherence risk.

    Risk is based on:
    - Confirmed missed-dose percentage
    - Consecutive missed doses per medication schedule
    - Recording coverage

    Missing records are UNKNOWN, not automatically MISSED.

    This is a rule-based prototype, not a clinically
    validated prediction model.
    """

    # Validate timestamps before sorting.
    for dose in doses:
        timestamp = dose.scheduled_for

        if (
            timestamp.tzinfo is None
            or timestamp.utcoffset() is None
        ):
            raise ValueError(
                "Dose timestamps must include a timezone"
            )

    ordered = sorted(
        doses,
        key=lambda dose: dose.scheduled_for,
    )

    total = len(ordered)

    if total == 0:
        return {
            "risk_level": "insufficient_data",
            "risk_score": None,
            "confidence": "none",
            "reasons": [
                "No expected doses available"
            ],
            "metrics": {
                "expected": 0,
                "recorded": 0,
                "missed": 0,
                "unrecorded": 0,
                "longest_missed_streak": 0,
            },
        }

    # Count dose statuses.
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

    # Calculate missed-dose streaks separately
    # for each medication schedule.
    streaks_by_schedule = {}
    longest_streak = 0

    for dose in ordered:
        schedule_key = dose.schedule_id

        if dose.status == AdherenceStatus.MISSED:
            streaks_by_schedule[schedule_key] = (
                streaks_by_schedule.get(
                    schedule_key, 0
                ) + 1
            )

            longest_streak = max(
                longest_streak,
                streaks_by_schedule[schedule_key],
            )
        else:
            streaks_by_schedule[schedule_key] = 0

    metrics = {
        "expected": total,
        "recorded": recorded,
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
        "unrecorded": unrecorded,
        "recording_coverage": round(
            coverage * 100, 2
        ),
        "longest_missed_streak": longest_streak,
    }

    # Do not assign a definitive risk level when
    # there is insufficient recorded evidence.
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

    missed_rate = missed / total

    score = 0
    reasons = []

    # Missed-dose percentage contribution.
    if missed_rate >= 0.5:
        score += 50
        reasons.append(
            "At least half of expected doses were missed"
        )

    elif missed_rate >= 0.25:
        score += 25
        reasons.append(
            "At least one quarter of doses were missed"
        )

    # Consecutive missed-dose contribution.
    if longest_streak >= 3:
        score += 30
        reasons.append(
            "Three or more consecutive missed doses"
        )

    elif longest_streak >= 2:
        score += 15
        reasons.append(
            "Two consecutive missed doses"
        )

    # Recording coverage contribution.
    if coverage < 0.8:
        score += 10
        reasons.append(
            "Some dose records are incomplete"
        )

    score = min(score, 100)

    # Final risk classification.
    if score >= 60:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"

    if not reasons:
        reasons.append(
            "No significant missed-dose pattern detected"
        )

    return {
        "risk_level": level,
        "risk_score": score,
        "confidence": (
            "high"
            if coverage >= 0.8
            else "moderate"
        ),
        "reasons": reasons,
        "metrics": metrics,
    }