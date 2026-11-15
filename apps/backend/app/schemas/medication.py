from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MedicationCreate(BaseModel):
    """Data accepted when adding a medication."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    dosage: str = Field(min_length=1, max_length=100)
    condition: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=500)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


class MedicationRead(BaseModel):
    """Medication information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    name: str
    dosage: str
    condition: str | None
    instructions: str | None
    start_date: date
    end_date: date | None
    is_active: bool
    created_at: datetime

class MedicationUpdate(BaseModel):
    """Optional fields accepted when updating a medication."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)
    dosage: str | None = Field(default=None, min_length=1, max_length=100)
    condition: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None