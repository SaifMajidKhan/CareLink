from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import User, UserRole
from app.services.audit_service import record_audit_event
from app.services.analytics_service import (
    get_patient_adherence_summary,
)
from app.services.risk_service import (
    get_patient_risk_assessment,
)
from app.services.caregiver_service import (
    caregiver_has_access,
)


router = APIRouter(
    prefix="/caregiver-dashboard",
    tags=["Caregiver Dashboard"],
)


def require_caregiver(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow only authenticated caregiver accounts."""

    if current_user.role != UserRole.CAREGIVER:
        raise HTTPException(
            status_code=403,
            detail="Caregiver account required",
        )

    return current_user


def verify_patient_access(
    db: Session,
    caregiver_id: UUID,
    patient_id: UUID,
) -> None:
    """
    Require an active patient-caregiver relationship.

    Return 404 for unauthorized patient IDs to avoid
    revealing whether another patient's account exists.
    """

    if not caregiver_has_access(
        db=db,
        caregiver_id=caregiver_id,
        patient_id=patient_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Linked patient not found",
        )


@router.get("/patients/{patient_id}/adherence")
def caregiver_patient_adherence(
    patient_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    caregiver: User = Depends(require_caregiver),
):
    """Read adherence analytics for an authorized patient."""

    verify_patient_access(
        db,
        caregiver.id,
        patient_id,
    )

    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="End date cannot precede start date",
        )

    if (end_date - start_date).days >= 90:
        raise HTTPException(
            status_code=422,
            detail="Date range cannot exceed 90 days",
        )

    if start_date > datetime.now(timezone.utc).date():
        raise HTTPException(
            status_code=422,
            detail="Start date cannot be in the future",
        )

    summary = get_patient_adherence_summary(
        db=db,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
    )

    record_audit_event(
        db=db,
        actor_user_id=caregiver.id,
        action="caregiver.adherence_viewed",
        entity_type="patient",
        entity_id=patient_id,
        details={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )

    db.commit()

    return summary


@router.get("/patients/{patient_id}/risk")
def caregiver_patient_risk(
    patient_id: UUID,
    db: Session = Depends(get_db),
    caregiver: User = Depends(require_caregiver),
):
    """Read risk analytics for an authorized patient."""

    verify_patient_access(
        db,
        caregiver.id,
        patient_id,
    )

    assessment = get_patient_risk_assessment(
        db=db,
        patient_id=patient_id,
    )

    record_audit_event(
        db=db,
        actor_user_id=caregiver.id,
        action="caregiver.risk_viewed",
        entity_type="patient",
        entity_id=patient_id,
        details={},
    )

    db.commit()

    return assessment