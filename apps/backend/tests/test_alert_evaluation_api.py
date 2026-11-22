from unittest.mock import patch

from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_caregiver_api import register_caregiver


ENDPOINT = "/analytics/risk/evaluate-alerts"


def setup_patient_and_caregiver(test_client, prefix):
    patient = register_and_login(
        test_client,
        f"{prefix}patient@example.com",
    )

    caregiver_email = f"{prefix}caregiver@example.com"

    caregiver = register_caregiver(
        test_client,
        caregiver_email,
    )

    response = test_client.post(
        "/caregivers",
        json={"caregiver_email": caregiver_email},
        headers=patient["headers"],
    )

    assert response.status_code == 201

    return patient, caregiver


def sample_risk(level="high", score=80):
    return {
        "risk_level": level,
        "risk_score": score,
        "confidence": "high",
        "trend": "declining",
        "metrics": {
            "expected": 10,
            "recorded": 10,
            "missed": 6,
        },
        "reasons": ["Repeated missed doses"],
    }


def test_patient_can_trigger_alert_evaluation(client):
    test_client, _ = client

    patient, caregiver = setup_patient_and_caregiver(
        test_client,
        "evaluate1",
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
    assert response.json()["should_alert"] is True
    assert response.json()["alerts_created"] == 1

    inbox = test_client.get(
        "/caregiver-alerts",
        headers=caregiver["headers"],
    )

    assert inbox.status_code == 200
    assert len(inbox.json()) == 1


def test_repeated_evaluation_does_not_duplicate_alert(client):
    test_client, _ = client

    patient, caregiver = setup_patient_and_caregiver(
        test_client,
        "evaluate2",
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

    assert first.json()["alerts_created"] == 1
    assert second.json()["alerts_created"] == 0
    assert second.json()["alerts_existing"] == 1

    inbox = test_client.get(
        "/caregiver-alerts",
        headers=caregiver["headers"],
    )

    assert len(inbox.json()) == 1


def test_caregiver_cannot_trigger_patient_evaluation(client):
    test_client, _ = client

    _, caregiver = setup_patient_and_caregiver(
        test_client,
        "evaluate3",
    )

    response = test_client.post(
        ENDPOINT,
        headers=caregiver["headers"],
    )

    assert response.status_code == 403


def test_anonymous_evaluation_is_rejected(client):
    test_client, _ = client

    response = test_client.post(ENDPOINT)

    assert response.status_code == 401


def test_low_risk_does_not_create_alert(client):
    test_client, _ = client

    patient, caregiver = setup_patient_and_caregiver(
        test_client,
        "evaluate5",
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
    assert response.json()["alerts_created"] == 0

    inbox = test_client.get(
        "/caregiver-alerts",
        headers=caregiver["headers"],
    )

    assert inbox.json() == []


def test_patient_without_caregivers_creates_no_alerts(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "evaluate6patient@example.com",
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
    assert response.json()["should_alert"] is True
    assert response.json()["alerts_created"] == 0
    assert response.json()["caregivers_processed"] == 0