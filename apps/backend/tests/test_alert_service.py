from uuid import UUID

import pytest

from app.services.alert_service import (
    AlertAccessDeniedError,
    AlertNotFoundError,
    acknowledge_caregiver_alert,
    assessment_fingerprint,
    create_caregiver_alert,
    list_caregiver_alerts,
)
from app.services.caregiver_service import (
    link_caregiver,
    revoke_caregiver,
)
from tests.test_registration import client


def create_account(test_client, email, caregiver=False):
    endpoint = (
        "/auth/register/caregiver"
        if caregiver
        else "/auth/register"
    )

    response = test_client.post(
        endpoint,
        json={
            "full_name": "Alert Test User",
            "email": email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


def sample_assessment(score=75):
    return {
        "risk_level": "high",
        "risk_score": score,
        "confidence": "high",
        "trend": "declining",
        "metrics": {
            "expected": 10,
            "missed": 6,
        },
        "reasons": [
            "Repeated missed doses",
        ],
    }


def setup_accounts(test_client, db, prefix):
    patient_id = create_account(
        test_client,
        f"{prefix}patient@example.com",
    )

    caregiver_email = f"{prefix}caregiver@example.com"

    caregiver_id = create_account(
        test_client,
        caregiver_email,
        caregiver=True,
    )

    link_caregiver(
        db,
        patient_id,
        caregiver_email,
    )

    return patient_id, caregiver_id


def create_alert(db, patient_id, caregiver_id, score=75):
    return create_caregiver_alert(
        db=db,
        patient_id=patient_id,
        caregiver_id=caregiver_id,
        assessment=sample_assessment(score),
        severity="high",
        title="High adherence risk",
        message="Repeated missed doses",
    )


def test_alert_can_be_created(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert1"
        )

        alert = create_alert(
            db, patient_id, caregiver_id
        )

        assert alert.id is not None
        assert alert.severity == "high"
        assert alert.is_acknowledged is False


def test_duplicate_assessment_does_not_create_duplicate_alert(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert2"
        )

        first = create_alert(
            db, patient_id, caregiver_id
        )

        second = create_alert(
            db, patient_id, caregiver_id
        )

        assert first.id == second.id

        alerts = list_caregiver_alerts(
            db, caregiver_id
        )

        assert len(alerts) == 1


def test_changed_assessment_creates_new_alert(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert3"
        )

        first = create_alert(
            db, patient_id, caregiver_id, 75
        )

        second = create_alert(
            db, patient_id, caregiver_id, 85
        )

        assert first.id != second.id


def test_unlinked_caregiver_cannot_receive_alert(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id = create_account(
            test_client, "alert4patient@example.com"
        )

        caregiver_id = create_account(
            test_client,
            "alert4caregiver@example.com",
            True,
        )

        with pytest.raises(AlertAccessDeniedError):
            create_alert(
                db, patient_id, caregiver_id
            )


def test_caregiver_can_acknowledge_alert(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert5"
        )

        alert = create_alert(
            db, patient_id, caregiver_id
        )

        updated = acknowledge_caregiver_alert(
            db,
            caregiver_id,
            alert.id,
        )

        assert updated.is_acknowledged is True
        assert updated.acknowledged_at is not None


def test_acknowledgment_is_idempotent(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert6"
        )

        alert = create_alert(
            db, patient_id, caregiver_id
        )

        first = acknowledge_caregiver_alert(
            db, caregiver_id, alert.id
        )

        timestamp = first.acknowledged_at

        second = acknowledge_caregiver_alert(
            db, caregiver_id, alert.id
        )

        assert second.acknowledged_at == timestamp


def test_revoked_caregiver_cannot_view_alerts(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert7"
        )

        create_alert(
            db, patient_id, caregiver_id
        )

        revoke_caregiver(
            db,
            patient_id,
            caregiver_id,
        )

        assert list_caregiver_alerts(
            db, caregiver_id
        ) == []


def test_revoked_caregiver_cannot_acknowledge_alert(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client, db, "alert8"
        )

        alert = create_alert(
            db, patient_id, caregiver_id
        )

        revoke_caregiver(
            db,
            patient_id,
            caregiver_id,
        )

        with pytest.raises(AlertNotFoundError):
            acknowledge_caregiver_alert(
                db,
                caregiver_id,
                alert.id,
            )


def test_assessment_fingerprint_is_stable():
    first = sample_assessment()
    second = sample_assessment()

    assert assessment_fingerprint(first) == (
        assessment_fingerprint(second)
    )


def test_assessment_change_updates_fingerprint():
    first = sample_assessment(75)
    second = sample_assessment(85)

    assert assessment_fingerprint(first) != (
        assessment_fingerprint(second)
    )