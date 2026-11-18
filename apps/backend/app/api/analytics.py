from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.medications import require_patient
from app.database import get_db
from app.models import User
from app.services.analytics_service import (
    get_patient_adherence_summary,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Adherence Analytics"],
)


@router.get("/adherence")
def get_adherence_analytics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    patient: User = Depends(require_patient),
):
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

    return get_patient_adherence_summary(
        db=db,
        patient_id=patient.id,
        start_date=start_date,
        end_date=end_date,
    )