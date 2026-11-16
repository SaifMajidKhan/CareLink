from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.medications import require_patient
from app.database import get_db
from app.models import User
from app.schemas.adherence import (
    AdherenceEventCreate,
    AdherenceEventRead,
)
from app.services.adherence_service import (
    DuplicateDoseEventError,
    InactiveScheduleError,
    InvalidDoseOccurrenceError,
    create_adherence_event,
    get_owned_schedule,
    list_adherence_events,
)

router = APIRouter(
    prefix="/medications",
    tags=["Adherence Tracking"],
)


@router.post(
    "/{medication_id}/schedules/{schedule_id}/events",
    response_model=AdherenceEventRead,
    status_code=201,
)
def record_dose(
    medication_id: UUID,
    schedule_id: UUID,
    data: AdherenceEventCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    schedule = get_owned_schedule(
        db, patient.id, medication_id, schedule_id
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found",
        )

    try:
        return create_adherence_event(
            db, schedule, patient.id, data
        )
    except InactiveScheduleError:
        raise HTTPException(
            status_code=409,
            detail="Schedule is inactive",
        )
    except InvalidDoseOccurrenceError:
        raise HTTPException(
            status_code=422,
            detail="Date or time does not match a past scheduled dose",
        )
    except DuplicateDoseEventError:
        raise HTTPException(
            status_code=409,
            detail="Dose event already recorded",
        )


@router.get(
    "/{medication_id}/schedules/{schedule_id}/events",
    response_model=list[AdherenceEventRead],
)
def get_dose_history(
    medication_id: UUID,
    schedule_id: UUID,
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
    schedule = get_owned_schedule(
        db, patient.id, medication_id, schedule_id
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found",
        )

    return list_adherence_events(db, schedule_id)