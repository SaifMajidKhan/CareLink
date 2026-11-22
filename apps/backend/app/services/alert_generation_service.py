from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.alert_engine import evaluate_caregiver_alert
from app.models import PatientCaregiver, User, UserRole
from app.services.alert_service import create_caregiver_alert
from app.services.risk_service import get_patient_risk_assessment


def generate_patient_caregiver_alerts(
    db: Session,
    patient_id: UUID,
) -> dict:
    """
    Evaluate a patient's adherence risk and generate
    alerts for actively linked caregivers.

    Must only be called by an authorized backend workflow.
    """

    assessment = get_patient_risk_assessment(
        db=db,
        patient_id=patient_id,
    )

    decision = evaluate_caregiver_alert(assessment)

    result = {
        "patient_id": str(patient_id),
        "risk_level": assessment["risk_level"],
        "risk_score": assessment["risk_score"],
        "should_alert": decision.should_alert,
        "caregivers_notified": 0,
        "alerts_created": 0,
        "alerts_existing": 0,
    }

    if not decision.should_alert:
        return result

    caregivers = list(
        db.scalars(
            select(PatientCaregiver.caregiver_id)
            .join(
                User,
                PatientCaregiver.caregiver_id == User.id,
            )
            .where(
                PatientCaregiver.patient_id == patient_id,
                PatientCaregiver.is_active.is_(True),
                User.role == UserRole.CAREGIVER,
                User.is_active.is_(True),
            )
        ).all()
    )

    from app.models import CaregiverAlert
    from app.services.alert_service import assessment_fingerprint

    fingerprint = assessment_fingerprint(assessment)

    for caregiver_id in caregivers:
        existing = db.scalar(
            select(CaregiverAlert).where(
                CaregiverAlert.patient_id == patient_id,
                CaregiverAlert.caregiver_id == caregiver_id,
                CaregiverAlert.assessment_fingerprint == fingerprint,
            )
        )

        create_caregiver_alert(
            db=db,
            patient_id=patient_id,
            caregiver_id=caregiver_id,
            assessment=assessment,
            severity=decision.severity,
            title=decision.title,
            message=decision.message,
        )

        result["caregivers_notified"] += 1

        if existing is None:
            result["alerts_created"] += 1
        else:
            result["alerts_existing"] += 1

    return result