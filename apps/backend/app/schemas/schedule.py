from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleCreate(BaseModel):
    """Data required to create a medication schedule."""

    model_config = ConfigDict(extra="forbid")

    scheduled_time: time
    days_of_week: list[int] = Field(default_factory=list)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError(
                "End date cannot be earlier than start date"
            )

        if any(day < 0 or day > 6 for day in self.days_of_week):
            raise ValueError("Weekdays must be between 0 and 6")

        if len(self.days_of_week) != len(set(self.days_of_week)):
            raise ValueError("Duplicate weekdays are not allowed")

        if self.scheduled_time.tzinfo is not None:
            raise ValueError(
                "Scheduled time must not contain a timezone offset"
            )

        return self


class ScheduleRead(BaseModel):
    """Schedule details returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    scheduled_time: time
    days_of_week: list[int]
    start_date: date
    end_date: date | None
    is_active: bool