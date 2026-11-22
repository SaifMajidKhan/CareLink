from uuid import UUID

from sqlalchemy import select

from app.models import AuditLog
from app.services.audit_service import (
    record_audit_event,
    list_audit_events,
)
from tests.test_registration import client
from tests.test_medications import register_and_login


def test_audit_event_can_be_recorded(client):
    test_client, TestSession = client

    patient = register_and_login(
        test_client,
        "audit1@example.com",
    )

    with TestSession() as db:
        audit = record_audit_event(
            db=db,
            actor_user_id=UUID(patient["id"]),
            action="test.action",
            entity_type="user",
            entity_id=patient["id"],
            details={"result": "success"},
        )

        db.commit()

        assert audit.id is not None

        stored = db.scalar(
            select(AuditLog).where(
                AuditLog.id == audit.id
            )
        )

        assert stored is not None
        assert stored.action == "test.action"
        assert stored.details["result"] == "success"


def test_audit_event_tracks_correct_actor(client):
    test_client, TestSession = client

    patient = register_and_login(
        test_client,
        "audit2@example.com",
    )

    with TestSession() as db:
        record_audit_event(
            db=db,
            actor_user_id=UUID(patient["id"]),
            action="test.access",
            entity_type="user",
            entity_id=patient["id"],
        )

        db.commit()

        events = list_audit_events(
            db,
            actor_user_id=UUID(patient["id"]),
        )

        assert len(events) == 1
        assert events[0].actor_user_id == UUID(
            patient["id"]
        )


def test_audit_event_supports_empty_details(client):
    test_client, TestSession = client

    patient = register_and_login(
        test_client,
        "audit3@example.com",
    )

    with TestSession() as db:
        audit = record_audit_event(
            db=db,
            actor_user_id=UUID(patient["id"]),
            action="test.empty",
            entity_type="user",
            entity_id=patient["id"],
        )

        db.commit()
        db.refresh(audit)

        assert audit.details == {}


def test_audit_event_rolls_back_with_transaction(client):
    test_client, TestSession = client

    patient = register_and_login(
        test_client,
        "audit4@example.com",
    )

    with TestSession() as db:
        record_audit_event(
            db=db,
            actor_user_id=UUID(patient["id"]),
            action="test.rollback",
            entity_type="user",
            entity_id=patient["id"],
        )

        db.rollback()

        events = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "test.rollback"
            )
        ).all()

        assert len(events) == 0


def test_audit_events_can_be_filtered_by_actor(client):
    test_client, TestSession = client

    first = register_and_login(
        test_client,
        "audit5first@example.com",
    )

    second = register_and_login(
        test_client,
        "audit5second@example.com",
    )

    with TestSession() as db:
        for user in (first, second):
            record_audit_event(
                db=db,
                actor_user_id=UUID(user["id"]),
                action="test.filter",
                entity_type="user",
                entity_id=user["id"],
            )

        db.commit()

        first_events = list_audit_events(
            db,
            actor_user_id=UUID(first["id"]),
        )

        assert len(first_events) == 1
        assert first_events[0].actor_user_id == UUID(
            first["id"]
        )