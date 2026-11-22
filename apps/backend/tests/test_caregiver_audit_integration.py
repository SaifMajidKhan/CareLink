from uuid import UUID
from unittest.mock import patch

import pytest

from sqlalchemy import select

from app.models import AuditLog, PatientCaregiver
from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_caregiver_api import register_caregiver


def setup_relationship(test_client, prefix):
    patient = register_and_login(
        test_client,
        f"{prefix}patient@example.com",
    )

    email = f"{prefix}caregiver@example.com"

    caregiver = register_caregiver(
        test_client,
        email,
    )

    return patient, caregiver, email


def test_linking_caregiver_creates_audit(client):
    test_client, TestSession = client

    patient, caregiver, email = setup_relationship(
        test_client, "auditlink1"
    )

    response = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=patient["headers"],
    )

    assert response.status_code == 201

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver.linked"
            )
        ).all()

        assert len(audits) == 1
        assert audits[0].actor_user_id == UUID(patient["id"])
        assert audits[0].entity_id == response.json()["id"]
        assert audits[0].details["caregiver_id"] == caregiver["id"]


def test_revoking_caregiver_creates_audit(client):
    test_client, TestSession = client

    patient, caregiver, email = setup_relationship(
        test_client, "auditlink2"
    )

    linked = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver.revoked"
            )
        ).all()

        assert len(audits) == 1
        assert audits[0].actor_user_id == UUID(patient["id"])
        assert audits[0].entity_id == linked.json()["id"]


def test_reactivation_creates_distinct_audit(client):
    test_client, TestSession = client

    patient, caregiver, email = setup_relationship(
        test_client, "auditlink3"
    )

    first = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=patient["headers"],
    )

    assert first.status_code == 201

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    reactivated = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=patient["headers"],
    )

    assert reactivated.status_code == 201
    assert reactivated.json()["id"] == first.json()["id"]

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.entity_id == first.json()["id"]
            )
        ).all()

        assert {audit.action for audit in audits} == {
            "caregiver.linked",
            "caregiver.revoked",
            "caregiver.reactivated",
        }


def test_unauthorized_revocation_creates_no_audit(client):
    test_client, TestSession = client

    owner, caregiver, email = setup_relationship(
        test_client, "auditlink4"
    )

    other = register_and_login(
        test_client,
        "auditlink4other@example.com",
    )

    linked = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=owner["headers"],
    )

    assert linked.status_code == 201

    response = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=other["headers"],
    )

    assert response.status_code == 404

    with TestSession() as db:
        revoked_audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver.revoked"
            )
        ).all()

        assert revoked_audits == []


def test_audit_failure_rolls_back_revocation(client):
    test_client, TestSession = client

    patient, caregiver, email = setup_relationship(
        test_client, "auditlink5"
    )

    linked = test_client.post(
        "/caregivers",
        json={"caregiver_email": email},
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    with patch(
        "app.services.caregiver_service.record_audit_event",
        side_effect=RuntimeError("Simulated audit failure"),
    ):
        with pytest.raises(RuntimeError):
            test_client.delete(
                f"/caregivers/{caregiver['id']}",
                headers=patient["headers"],
            )

    with TestSession() as db:
        relationship = db.get(
            PatientCaregiver,
            UUID(linked.json()["id"]),
        )

        assert relationship.is_active is True

        revoked_audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver.revoked"
            )
        ).all()

        assert revoked_audits == []