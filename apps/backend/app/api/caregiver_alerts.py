from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.caregiver_dashboard import require_caregiver
from app.database import get_db
from app.models import User
from app.schemas.alert import CaregiverAlertRead
from app.services.alert_service import (
    AlertNotFoundError,
    acknowledge_caregiver_alert,
    list_caregiver_alerts,
)


router = APIRouter(
    prefix="/caregiver-alerts",
    tags=["Caregiver Alerts"],
)


@router.get(
    "",
    response_model=list[CaregiverAlertRead],
)
def get_my_alerts(
    unacknowledged_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    caregiver: User = Depends(require_caregiver),
):
    """List alerts for patients this caregiver may access."""

    alerts = list_caregiver_alerts(
        db=db,
        caregiver_id=caregiver.id,
    )

    if unacknowledged_only:
        alerts = [
            alert
            for alert in alerts
            if not alert.is_acknowledged
        ]

    return alerts


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=CaregiverAlertRead,
)
def acknowledge_my_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    caregiver: User = Depends(require_caregiver),
):
    """Acknowledge an alert belonging to this caregiver."""

    try:
        return acknowledge_caregiver_alert(
            db=db,
            caregiver_id=caregiver.id,
            alert_id=alert_id,
        )

    except AlertNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )