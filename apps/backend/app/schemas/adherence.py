from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AdherenceStatus


class AdherenceEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_for: datetime
    status: AdherenceStatus
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("scheduled_for")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduled_for must include a timezone")

        return value

    @field_validator("status")
    @classmethod
    def reject_unknown(cls, value: AdherenceStatus) -> AdherenceStatus:
        if value == AdherenceStatus.UNKNOWN:
            raise ValueError("Use taken, missed or skipped")

        return value


class AdherenceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_id: UUID
    recorded_by_user_id: UUID
    scheduled_for: datetime
    status: AdherenceStatus
    notes: str | None
    recorded_at: datetime