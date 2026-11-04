import re
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, field_validator, model_validator

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    @field_validator('email', mode='before')
    @classmethod
    def email_valid(cls, value):
        if not isinstance(value, str): raise ValueError('Enter a valid email address')
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

class Registration(Credentials):
    name: str = Field(min_length=1, max_length=80)
    role: Literal['patient', 'caregiver'] = 'patient'
    @field_validator('name', mode='before')
    @classmethod
    def name_valid(cls, value):
        if not isinstance(value, str) or not value.strip(): raise ValueError('Name is required')
        return value.strip()

class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    condition: Literal['', 'hypertension', 'diabetes', 'both'] = ''

class Schedule(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    instructions: str = Field(min_length=1, max_length=300)
    times: list[str] = Field(min_length=1, max_length=8)
    start: date
    end: date | None = None
    timezone: str = 'Asia/Karachi'
    @field_validator('times')
    @classmethod
    def times_valid(cls, values):
        import re
        if len(set(values)) != len(values) or any(not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v) for v in values):
            raise ValueError('Use unique daily times in HH:MM format')
        return sorted(values)
    @field_validator('timezone')
    @classmethod
    def zone_valid(cls, value):
        try: ZoneInfo(value)
        except Exception: raise ValueError('Unknown timezone')
        return value
    @model_validator(mode='after')
    def range_valid(self):
        if self.end and self.end < self.start: raise ValueError('End precedes start')
        if not self.name.strip() or not self.instructions.strip(): raise ValueError('Name and instructions required')
        return self

class StopSchedule(BaseModel):
    end: date

class DoseReport(BaseModel):
    request_id: str = Field(min_length=8, max_length=80)
    schedule_id: str = Field(min_length=1, max_length=80)
    day: date
    time: str
    outcome: Literal['taken', 'skipped']
    taken_at: datetime | None = None
    recorded_at: datetime
    approximate: bool = False
    expected_version: int = Field(default=0, ge=0)
    reason: str = Field(default='', max_length=300)
    @model_validator(mode='after')
    def time_valid(self):
        from datetime import timezone, timedelta
        now = datetime.now(timezone.utc) + timedelta(minutes=2)
        for t in (self.taken_at, self.recorded_at):
            if t and (t.tzinfo is None or t > now): raise ValueError('Times must include timezone and not be in the future')
        if self.outcome == 'taken' and self.taken_at is None: raise ValueError('Taken time required')
        if self.taken_at and self.taken_at > self.recorded_at: raise ValueError('Taken time cannot follow the report entry time')
        if self.outcome == 'skipped' and (self.taken_at or self.approximate): raise ValueError('Skipped has no taken time')
        if self.expected_version and not self.reason.strip(): raise ValueError('Explain the correction')
        return self

class Reading(BaseModel):
    kind: Literal['blood_pressure', 'glucose']
    value: float = Field(gt=0, le=1000)
    secondary: float | None = Field(default=None, gt=0, le=300)
    unit: Literal['mmHg', 'mg/dL', 'mmol/L']
    measured_at: datetime
    @model_validator(mode='after')
    def reading_valid(self):
        from datetime import timezone
        if self.measured_at.tzinfo is None or self.measured_at > datetime.now(timezone.utc): raise ValueError('Choose a past time with timezone')
        if self.kind == 'blood_pressure' and (self.unit != 'mmHg' or self.secondary is None or self.secondary >= self.value): raise ValueError('Enter systolic above diastolic, in mmHg')
        if self.kind == 'glucose' and (self.unit == 'mmHg' or self.secondary is not None): raise ValueError('Choose a glucose unit')
        return self

class RequestConnection(BaseModel):
    patient_id: str = Field(min_length=1, max_length=100)

class Decision(BaseModel):
    action: Literal['accept', 'decline', 'remove', 'leave']

class Note(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class AccountStatus(BaseModel):
    enabled: bool

class Assignment(BaseModel):
    patient_id: str
    coordinator_id: str
