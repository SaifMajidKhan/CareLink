from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CaregiverAlertRead(BaseModel):
    """Safe alert information returned to a caregiver."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    caregiver_id: UUID

    severity: str
    title: str
    message: str
    risk_score: int | None

    is_acknowledged: bool
    created_at: datetime
    acknowledged_at: datetime | None