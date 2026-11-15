import uuid

from datetime import date, datetime, time, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    PATIENT = "patient"
    CAREGIVER = "caregiver"
    COORDINATOR = "coordinator"
    ADMIN = "admin"


class AdherenceStatus(str, Enum):
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    patient_links: Mapped[list["PatientCaregiver"]] = relationship(
        back_populates="patient",
        foreign_keys="PatientCaregiver.patient_id",
    )
    caregiver_links: Mapped[list["PatientCaregiver"]] = relationship(
        back_populates="caregiver",
        foreign_keys="PatientCaregiver.caregiver_id",
    )
    medications: Mapped[list["Medication"]] = relationship(
        back_populates="patient"
    )


class PatientCaregiver(Base):
    __tablename__ = "patient_caregivers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    patient: Mapped["User"] = relationship(
        back_populates="patient_links",
        foreign_keys=[patient_id],
    )
    caregiver: Mapped["User"] = relationship(
        back_populates="caregiver_links",
        foreign_keys=[caregiver_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "patient_id", "caregiver_id",
            name="uq_patient_caregivers_patient_caregiver",
        ),
    )


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    instructions: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    patient: Mapped["User"] = relationship(back_populates="medications")
    schedules: Mapped[list["MedicationSchedule"]] = relationship(
        back_populates="medication",
        cascade="all, delete-orphan",
    )


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    medication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medications.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    days_of_week: Mapped[list[int]] = mapped_column(
        JSON, default=list, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    medication: Mapped["Medication"] = relationship(
        back_populates="schedules"
    )
    adherence_events: Mapped[list["AdherenceEvent"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


class AdherenceEvent(Base):
    __tablename__ = "adherence_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medication_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[AdherenceStatus] = mapped_column(
        SQLAlchemyEnum(
            AdherenceStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
        ),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    schedule: Mapped["MedicationSchedule"] = relationship(
        back_populates="adherence_events"
    )

    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "scheduled_for",
            name="uq_adherence_schedule_occurrence",
        ),
        Index("ix_adherence_scheduled_for", "scheduled_for"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )