from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select

from app.models import AuditLog
from tests.test_registration import client
from tests.test_alert_evaluation_api import (
    ENDPOINT,
    sample_risk,
    setup_patient_and_caregiver,
)
from tests.test_medications import register_and_login
from tests.test_caregiver_api import register_caregiver


AUDIT_ACTION = "patient.risk_alerts_evaluated"


def get_evaluation_audits(db):
    return list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.action == AUDIT_ACTION
            )
        ).all()
    )


def test_high_risk_evaluation_creates_audit(client):
    test_client, TestSession = client

    patient, _ = setup_patient_and_caregiver(
        test_client,
        "evalaudit1",
    )

    with patch(
        "app.services.alert_generation_service.get_patient_risk_assessment",
        return_value=sample_risk(),
    ):
        response = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

    assert response.status_code == 200
    assert response.json()["alerts_created"] == 1

    with TestSession() as db:
        audits = get_evaluation_audits(db)

        assert len(audits) == 1
        assert audits[0].actor_user_id == UUID(patient["id"])
        assert audits[0].entity_type == "patient"
        assert audits[0].entity_id == patient["id"]

        assert audits[0].details == {
            "should_alert": True,
            "alerts_created": 1,
            "alerts_existing": 0,
            "caregivers_processed": 1,
        }


def test_low_risk_evaluation_is_audited(client):
    test_client, TestSession = client

    patient, _ = setup_patient_and_caregiver(
        test_client,
        "evalaudit2",
    )

    with patch(
        "app.services.alert_generation_service.get_patient_risk_assessment",
        return_value=sample_risk("low", 10),
    ):
        response = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

    assert response.status_code == 200
    assert response.json()["should_alert"] is False

    with TestSession() as db:
        audits = get_evaluation_audits(db)

        assert len(audits) == 1
        assert audits[0].details["should_alert"] is False
        assert audits[0].details["alerts_created"] == 0


def test_repeated_evaluations_have_separate_audits(client):
    test_client, TestSession = client

    patient, _ = setup_patient_and_caregiver(
        test_client,
        "evalaudit3",
    )

    with patch(
        "app.services.alert_generation_service.get_patient_risk_assessment",
        return_value=sample_risk(),
    ):
        first = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

        second = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

    assert first.status_code == 200
    assert second.status_code == 200

    with TestSession() as db:
        audits = get_evaluation_audits(db)

        assert len(audits) == 2

        created_counts = sorted(
            audit.details["alerts_created"]
            for audit in audits
        )

        assert created_counts == [0, 1]


def test_caregiver_cannot_create_evaluation_audit(client):
    test_client, TestSession = client

    caregiver = register_caregiver(
        test_client,
        "evalaudit4caregiver@example.com",
    )

    response = test_client.post(
        ENDPOINT,
        headers=caregiver["headers"],
    )

    assert response.status_code == 403

    with TestSession() as db:
        assert get_evaluation_audits(db) == []


def test_anonymous_evaluation_creates_no_audit(client):
    test_client, TestSession = client

    response = test_client.post(ENDPOINT)

    assert response.status_code == 401

    with TestSession() as db:
        assert get_evaluation_audits(db) == []


def test_patient_without_caregivers_still_has_audit(client):
    test_client, TestSession = client

    patient = register_and_login(
        test_client,
        "evalaudit6patient@example.com",
    )

    with patch(
        "app.services.alert_generation_service.get_patient_risk_assessment",
        return_value=sample_risk(),
    ):
        response = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

    assert response.status_code == 200
    assert response.json()["alerts_created"] == 0
    assert response.json()["caregivers_processed"] == 0

    with TestSession() as db:
        audits = get_evaluation_audits(db)

        assert len(audits) == 1
        assert audits[0].details["should_alert"] is True
        assert audits[0].details["caregivers_processed"] == 0