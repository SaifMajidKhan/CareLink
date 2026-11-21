from datetime import datetime, timedelta, timezone

from app.analytics.risk_engine import RiskDose
from app.models import AdherenceStatus


def calculate_adherence_trend(
    doses: list[RiskDose],
    as_of: datetime,
) -> dict:
    """
    Compare the latest 7 days against the preceding 7 days.

    Only expected dose occurrences up to as_of are included.
    Uses recorded-dose adherence, not unrecorded doses as misses.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")

    cutoff = as_of.astimezone(timezone.utc)
    recent_start = cutoff - timedelta(days=7)
    previous_start = cutoff - timedelta(days=14)

    previous = []
    recent = []
    seen = set()

    for dose in doses:
        timestamp = dose.scheduled_for

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Dose timestamps must include a timezone")

        timestamp = timestamp.astimezone(timezone.utc)

        if timestamp in seen:
            # Identical times may legitimately belong to different
            # schedules. RiskDose currently lacks schedule identity,
            # so do not deduplicate by timestamp.
            pass

        seen.add(timestamp)

        if previous_start <= timestamp < recent_start:
            previous.append(dose)
        elif recent_start <= timestamp <= cutoff:
            recent.append(dose)

    def summarize(period: list[RiskDose]) -> dict:
        expected = len(period)

        taken = sum(
            dose.status == AdherenceStatus.TAKEN
            for dose in period
        )
        missed = sum(
            dose.status == AdherenceStatus.MISSED
            for dose in period
        )
        skipped = sum(
            dose.status == AdherenceStatus.SKIPPED
            for dose in period
        )

        recorded = taken + missed + skipped

        coverage = (
            round(recorded / expected * 100, 2)
            if expected
            else 0.0
        )

        rate = (
            round(taken / recorded * 100, 2)
            if recorded
            else None
        )

        sufficient = recorded >= 3 and (
            recorded / expected >= 0.5
            if expected
            else False
        )

        return {
            "expected": expected,
            "recorded": recorded,
            "taken": taken,
            "missed": missed,
            "skipped": skipped,
            "unrecorded": expected - recorded,
            "recording_coverage": coverage,
            "recorded_adherence_rate": rate,
            "sufficient_data": sufficient,
        }

    previous_summary = summarize(previous)
    recent_summary = summarize(recent)

    if not (
        previous_summary["sufficient_data"]
        and recent_summary["sufficient_data"]
    ):
        trend = "insufficient_data"
        change = None
    else:
        change = round(
            recent_summary["recorded_adherence_rate"]
            - previous_summary["recorded_adherence_rate"],
            2,
        )

        if change <= -10:
            trend = "declining"
        elif change >= 10:
            trend = "improving"
        else:
            trend = "stable"

    return {
        "trend": trend,
        "change_percentage_points": change,
        "previous_7_days": previous_summary,
        "recent_7_days": recent_summary,
    }