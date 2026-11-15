from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.medications import require_patient
from app.database import get_db
from app.models import User
from app.schemas.schedule import ScheduleCreate, ScheduleRead
from app.services.schedule_service import (
    InactiveMedicationError,
    InvalidScheduleDatesError,
    create_schedule,
    list_medication_schedules,
)

router = APIRouter(
    prefix="/medications",
    tags=["Medication Schedules"],
)


@router.post(
    "/{medication_id}/schedules",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
)
def add_schedule(
    medication_id: UUID,
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    try:
        schedule = create_schedule(
            db, patient.id, medication_id, data
        )
    except InactiveMedicationError:
        raise HTTPException(
            status_code=409,
            detail="Cannot schedule an inactive medication",
        )
    except InvalidScheduleDatesError:
        raise HTTPException(
            status_code=422,
            detail="Schedule dates must fit medication dates",
        )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Medication not found",
        )

    return schedule


@router.get(
    "/{medication_id}/schedules",
    response_model=list[ScheduleRead],
)
def get_schedules(
    medication_id: UUID,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    schedules = list_medication_schedules(
        db, patient.id, medication_id
    )

    if schedules is None:
        raise HTTPException(
            status_code=404,
            detail="Medication not found",
        )

    return schedules