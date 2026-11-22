from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PatientCaregiver, User, UserRole
from app.services.audit_service import record_audit_event


class CaregiverNotFoundError(Exception):
    pass


class CaregiverAlreadyLinkedError(Exception):
    pass


class CaregiverLinkNotFoundError(Exception):
    pass


def link_caregiver(
    db: Session,
    patient_id: UUID,
    caregiver_email: str,
    relationship_type: str | None = None,
) -> PatientCaregiver:
    """
    Create or reactivate a patient-caregiver relationship.

    Only an active caregiver account may be linked.
    Authorization of the patient must be enforced by
    the API layer before calling this service.
    """

    email = caregiver_email.strip().lower()

    caregiver = db.scalar(
        select(User).where(
            User.email == email,
            User.role == UserRole.CAREGIVER,
            User.is_active.is_(True),
        )
    )

    if caregiver is None:
        raise CaregiverNotFoundError()

    existing = db.scalar(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == caregiver.id,
        )
    )

    if existing is not None:
        if existing.is_active:
            raise CaregiverAlreadyLinkedError()

        existing.is_active = True
        existing.relationship_type = relationship_type

        record_audit_event(
            db=db,
            actor_user_id=patient_id,
            action="caregiver.reactivated",
            entity_type="patient_caregiver",
            entity_id=existing.id,
            details={"caregiver_id": str(caregiver.id)},
        )

        db.commit()
        db.refresh(existing)

        return existing

    relationship = PatientCaregiver(
        patient_id=patient_id,
        caregiver_id=caregiver.id,
        relationship_type=relationship_type,
        is_active=True,
    )

    db.add(relationship)
    db.flush()

    record_audit_event(
        db=db,
        actor_user_id=patient_id,
        action="caregiver.linked",
        entity_type="patient_caregiver",
        entity_id=relationship.id,
        details={"caregiver_id": str(caregiver.id)},
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CaregiverAlreadyLinkedError()

    db.refresh(relationship)

    return relationship


def list_patient_caregivers(
    db: Session,
    patient_id: UUID,
) -> list[PatientCaregiver]:
    """List active caregiver relationships for a patient."""

    return list(
        db.scalars(
            select(PatientCaregiver)
            .where(
                PatientCaregiver.patient_id == patient_id,
                PatientCaregiver.is_active.is_(True),
            )
            .order_by(PatientCaregiver.created_at)
        ).all()
    )


def revoke_caregiver(
    db: Session,
    patient_id: UUID,
    caregiver_id: UUID,
) -> PatientCaregiver:
    """Revoke an active caregiver relationship."""

    relationship = db.scalar(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == caregiver_id,
            PatientCaregiver.is_active.is_(True),
        )
    )

    if relationship is None:
        raise CaregiverLinkNotFoundError()

    relationship.is_active = False

    record_audit_event(
        db=db,
        actor_user_id=patient_id,
        action="caregiver.revoked",
        entity_type="patient_caregiver",
        entity_id=relationship.id,
        details={"caregiver_id": str(caregiver_id)},
    )

    db.commit()
    db.refresh(relationship)

    return relationship


def caregiver_has_access(
    db: Session,
    caregiver_id: UUID,
    patient_id: UUID,
) -> bool:
    """Check whether an active caregiver can access a patient."""

    relationship = db.scalar(
        select(PatientCaregiver)
        .join(
            User,
            PatientCaregiver.caregiver_id == User.id,
        )
        .where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == caregiver_id,
            PatientCaregiver.is_active.is_(True),
            User.role == UserRole.CAREGIVER,
            User.is_active.is_(True),
        )
    )

    return relationship is not None