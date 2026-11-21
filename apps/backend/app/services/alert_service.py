import hashlib
import json

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CaregiverAlert, PatientCaregiver
from app.services.caregiver_service import caregiver_has_access


class AlertAccessDeniedError(Exception):
    pass


class AlertNotFoundError(Exception):
    pass


def assessment_fingerprint(assessment: dict) -> str:
    """
    Create a stable fingerprint from the assessment result.

    Identical assessment results produce the same fingerprint.
    """

    relevant = {
        "risk_level": assessment["risk_level"],
        "risk_score": assessment["risk_score"],
        "confidence": assessment["confidence"],
        "trend": assessment.get("trend"),
        "metrics": assessment.get("metrics", {}),
        "reasons": assessment.get("reasons", []),
    }

    payload = json.dumps(
        relevant,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def create_caregiver_alert(
    db: Session,
    patient_id: UUID,
    caregiver_id: UUID,
    assessment: dict,
    severity: str,
    title: str,
    message: str,
) -> CaregiverAlert:
    """
    Create an alert for an authorized caregiver.

    Identical assessments will not create duplicate alerts.
    """

    if not caregiver_has_access(
        db,
        caregiver_id,
        patient_id,
    ):
        raise AlertAccessDeniedError()

    fingerprint = assessment_fingerprint(assessment)

    existing = db.scalar(
        select(CaregiverAlert).where(
            CaregiverAlert.patient_id == patient_id,
            CaregiverAlert.caregiver_id == caregiver_id,
            CaregiverAlert.assessment_fingerprint == fingerprint,
        )
    )

    if existing is not None:
        return existing

    alert = CaregiverAlert(
        patient_id=patient_id,
        caregiver_id=caregiver_id,
        severity=severity,
        title=title,
        message=message,
        risk_score=assessment["risk_score"],
        assessment_fingerprint=fingerprint,
        is_acknowledged=False,
    )

    db.add(alert)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existing = db.scalar(
            select(CaregiverAlert).where(
                CaregiverAlert.patient_id == patient_id,
                CaregiverAlert.caregiver_id == caregiver_id,
                CaregiverAlert.assessment_fingerprint == fingerprint,
            )
        )

        if existing is None:
            raise

        return existing

    db.refresh(alert)

    return alert


def list_caregiver_alerts(
    db: Session,
    caregiver_id: UUID,
) -> list[CaregiverAlert]:
    """
    Return alerts belonging to this caregiver,
    excluding patients whose access was revoked.
    """

    return list(
        db.scalars(
            select(CaregiverAlert)
            .join(
                PatientCaregiver,
                (
                    CaregiverAlert.patient_id
                    == PatientCaregiver.patient_id
                )
                & (
                    CaregiverAlert.caregiver_id
                    == PatientCaregiver.caregiver_id
                ),
            )
            .where(
                CaregiverAlert.caregiver_id == caregiver_id,
                PatientCaregiver.is_active.is_(True),
            )
            .order_by(CaregiverAlert.created_at.desc())
        ).all()
    )


def acknowledge_caregiver_alert(
    db: Session,
    caregiver_id: UUID,
    alert_id: UUID,
) -> CaregiverAlert:
    """
    Acknowledge an alert owned by the caregiver,
    provided patient access is still active.
    """

    alert = db.scalar(
        select(CaregiverAlert).where(
            CaregiverAlert.id == alert_id,
            CaregiverAlert.caregiver_id == caregiver_id,
        )
    )

    if alert is None:
        raise AlertNotFoundError()

    if not caregiver_has_access(
        db,
        caregiver_id,
        alert.patient_id,
    ):
        raise AlertNotFoundError()

    if not alert.is_acknowledged:
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(alert)

    return alert