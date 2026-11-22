from uuid import UUID
from unittest.mock import patch

import pytest

from sqlalchemy import select

from app.models import AuditLog, CaregiverAlert
from tests.test_registration import client
from tests.test_caregiver_alert_api import setup_alert
from tests.test_caregiver_api import register_caregiver


def test_acknowledgment_creates_audit_record(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client, TestSession, "auditalert1"
    )

    response = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=caregiver["headers"],
    )

    assert response.status_code == 200

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver_alert.acknowledged",
                AuditLog.entity_id == alert_id,
            )
        ).all()

        assert len(audits) == 1
        assert audits[0].actor_user_id == UUID(
            str(caregiver["id"])
        )
        assert audits[0].entity_type == "caregiver_alert"


def test_repeated_acknowledgment_creates_only_one_audit(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client, TestSession, "auditalert2"
    )

    url = f"/caregiver-alerts/{alert_id}/acknowledge"

    first = test_client.patch(
        url, headers=caregiver["headers"]
    )
    second = test_client.patch(
        url, headers=caregiver["headers"]
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver_alert.acknowledged",
                AuditLog.entity_id == alert_id,
            )
        ).all()

        assert len(audits) == 1


def test_unauthorized_acknowledgment_creates_no_audit(client):
    test_client, TestSession = client

    _, _, _, alert_id = setup_alert(
        test_client, TestSession, "auditalert3"
    )

    outsider = register_caregiver(
        test_client,
        "auditalert3outsider@example.com",
    )

    response = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=outsider["headers"],
    )

    assert response.status_code == 404

    with TestSession() as db:
        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver_alert.acknowledged",
                AuditLog.entity_id == alert_id,
            )
        ).all()

        assert audits == []


def test_audit_failure_rolls_back_acknowledgment(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client, TestSession, "auditalert4"
    )

    with patch(
        "app.services.alert_service.record_audit_event",
        side_effect=RuntimeError("Simulated audit failure"),
    ):
        with pytest.raises(RuntimeError):
            test_client.patch(
                f"/caregiver-alerts/{alert_id}/acknowledge",
                headers=caregiver["headers"],
            )

    with TestSession() as db:
        alert = db.get(
            CaregiverAlert,
            UUID(alert_id),
        )

        assert alert.is_acknowledged is False
        assert alert.acknowledged_at is None

        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "caregiver_alert.acknowledged",
                AuditLog.entity_id == alert_id,
            )
        ).all()

        assert audits == []