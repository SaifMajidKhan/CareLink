from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit_event(
    db: Session,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    details: dict | None = None,
) -> AuditLog:
    """
    Stage an audit event in the current transaction.

    The caller is responsible for committing.
    Avoid storing passwords, tokens, medication notes,
    or unnecessary patient information in details.
    """

    audit = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
    )

    db.add(audit)
    db.flush()

    return audit


def list_audit_events(
    db: Session,
    actor_user_id: UUID | None = None,
) -> list[AuditLog]:
    """
    Internal audit query helper.

    Do not expose this directly through a public API.
    """

    query = select(AuditLog)

    if actor_user_id is not None:
        query = query.where(
            AuditLog.actor_user_id == actor_user_id
        )

    query = query.order_by(
        AuditLog.created_at.desc()
    )

    return list(db.scalars(query).all())