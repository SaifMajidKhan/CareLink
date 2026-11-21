from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.medications import require_patient
from app.database import get_db
from app.models import User
from app.schemas.caregiver import (
    CaregiverLinkCreate,
    CaregiverLinkRead,
)
from app.services.caregiver_service import (
    CaregiverAlreadyLinkedError,
    CaregiverLinkNotFoundError,
    CaregiverNotFoundError,
    link_caregiver,
    list_patient_caregivers,
    revoke_caregiver,
)


router = APIRouter(
    prefix="/caregivers",
    tags=["Caregiver Management"],
)


@router.post(
    "",
    response_model=CaregiverLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_caregiver(
    data: CaregiverLinkCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    """
    Allow an authenticated patient to link an
    existing caregiver account.
    """

    try:
        return link_caregiver(
            db=db,
            patient_id=patient.id,
            caregiver_email=str(data.caregiver_email),
            relationship_type=data.relationship_type,
        )

    except CaregiverNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Active caregiver account not found",
        )

    except CaregiverAlreadyLinkedError:
        raise HTTPException(
            status_code=409,
            detail="Caregiver is already linked",
        )


@router.get(
    "",
    response_model=list[CaregiverLinkRead],
)
def get_my_caregivers(
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    """Return the patient's active caregiver relationships."""

    return list_patient_caregivers(
        db=db,
        patient_id=patient.id,
    )


@router.delete(
    "/{caregiver_id}",
    response_model=CaregiverLinkRead,
)
def remove_caregiver(
    caregiver_id: UUID,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    """Revoke a caregiver's access to this patient."""

    try:
        return revoke_caregiver(
            db=db,
            patient_id=patient.id,
            caregiver_id=caregiver_id,
        )

    except CaregiverLinkNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Active caregiver relationship not found",
        )