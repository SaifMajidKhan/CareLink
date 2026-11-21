from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_adherence import (
    create_patient_medication_schedule,
)


RISK_URL = "/analytics/risk"


def test_risk_endpoint_requires_authentication(client):
    test_client, _ = client

    response = test_client.get(RISK_URL)

    assert response.status_code == 401


def test_patient_can_access_risk_assessment(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "riskapi1@example.com",
    )

    response = test_client.get(
        RISK_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert "risk_level" in data
    assert "risk_score" in data
    assert "confidence" in data
    assert "reasons" in data
    assert "metrics" in data
    assert "trend" in data
    assert "trend_details" in data

    assert data["clinical_prediction"] is False


def test_risk_endpoint_returns_insufficient_data_for_new_patient(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "riskapi2@example.com",
    )

    response = test_client.get(
        RISK_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["risk_level"] == "insufficient_data"
    assert data["risk_score"] is None
    assert data["metrics"]["expected"] == 0


def test_patient_cannot_access_another_patients_risk_data(client):
    test_client, _ = client

    create_patient_medication_schedule(
        test_client,
        "riskapiowner@example.com",
    )

    other_patient = register_and_login(
        test_client,
        "riskapiother@example.com",
    )

    response = test_client.get(
        RISK_URL,
        headers=other_patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["metrics"]["expected"] == 0


def test_risk_response_includes_assessment_metadata(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "riskapimetadata@example.com",
    )

    response = test_client.get(
        RISK_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["assessment_type"] == (
        "rule_based_adherence_risk"
    )
    assert "assessment_time" in data
    assert "window_start" in data
    assert "window_end" in data
    assert "unknown_deactivation_schedules" in data
    assert "historical_accuracy_warning" in data