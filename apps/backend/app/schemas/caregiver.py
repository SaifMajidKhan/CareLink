from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CaregiverLinkCreate(BaseModel):
    """Information supplied by a patient when linking a caregiver."""

    model_config = ConfigDict(extra="forbid")

    caregiver_email: EmailStr
    relationship_type: str | None = Field(
        default=None,
        max_length=50,
    )


class CaregiverLinkRead(BaseModel):
    """Safe information returned for a caregiver relationship."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    caregiver_id: UUID
    relationship_type: str | None
    is_active: bool
    created_at: datetime