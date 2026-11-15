from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import User, UserRole
from app.schemas.medication import (
    MedicationCreate,
    MedicationRead,
    MedicationUpdate,
)
from app.services.medication_service import (
    create_medication,
    get_patient_medication,
    list_patient_medications,
    InvalidMedicationDatesError,
    update_medication,
    deactivate_medication,
)

router = APIRouter(
    prefix="/medications",
    tags=["Medications"],
)


def require_patient(
    current_user: User = Depends(get_current_user),
) -> User:
    """Restrict medication management to patient accounts."""

    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account required",
        )

    return current_user


@router.post(
    "",
    response_model=MedicationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_medication(
    data: MedicationCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    return create_medication(db, patient.id, data)


@router.get("", response_model=list[MedicationRead])
def get_my_medications(
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    return list_patient_medications(db, patient.id)


@router.get("/{medication_id}", response_model=MedicationRead)
def get_medication(
    medication_id: UUID,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    medication = get_patient_medication(
        db,
        patient.id,
        medication_id,
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    return medication

@router.patch(
    "/{medication_id}",
    response_model=MedicationRead,
)
def edit_medication(
    medication_id: UUID,
    data: MedicationUpdate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    medication = get_patient_medication(
        db,
        patient.id,
        medication_id,
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    if not medication.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive medication cannot be edited",
        )

    try:
        return update_medication(db, medication, data)

    except InvalidMedicationDatesError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End date cannot be earlier than start date",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )


@router.patch(
    "/{medication_id}/deactivate",
    response_model=MedicationRead,
)
def deactivate_my_medication(
    medication_id: UUID,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    medication = get_patient_medication(
        db,
        patient.id,
        medication_id,
    )

    if medication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    return deactivate_medication(db, medication)