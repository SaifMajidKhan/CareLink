from tests.test_registration import client
from tests.test_caregiver_api import register_caregiver
from tests.test_medications import register_and_login
from uuid import UUID

from app.services.alert_service import create_caregiver_alert


def setup_alert(test_client, TestSession, prefix):
    patient_email = f"{prefix}patient@example.com"
    caregiver_email = f"{prefix}caregiver@example.com"

    patient = register_and_login(
        test_client,
        patient_email,
    )

    caregiver = register_caregiver(
        test_client,
        caregiver_email,
    )

    profile = test_client.get(
        "/auth/me",
        headers=patient["headers"],
    )

    assert profile.status_code == 200
    patient_id = profile.json()["id"]

    linked = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": caregiver_email,
        },
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    with TestSession() as db:
        alert = create_caregiver_alert(
            db=db,
            patient_id=UUID(patient_id),
            caregiver_id=UUID(str(caregiver["id"])),
            assessment={
                "risk_level": "high",
                "risk_score": 80,
                "confidence": "high",
                "trend": "declining",
                "metrics": {
                    "expected": 10,
                    "missed": 6,
                },
                "reasons": ["Repeated missed doses"],
            },
            severity="high",
            title="High adherence risk",
            message="Repeated missed doses",
        )

        alert_id = str(alert.id)

    return patient, caregiver, patient_id, alert_id


def test_caregiver_can_list_alerts(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client,
        TestSession,
        "inbox1",
    )

    response = test_client.get(
        "/caregiver-alerts",
        headers=caregiver["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == alert_id
    assert response.json()[0]["severity"] == "high"


def test_caregiver_can_acknowledge_alert(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client,
        TestSession,
        "inbox2",
    )

    response = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=caregiver["headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_acknowledged"] is True
    assert response.json()["acknowledged_at"] is not None


def test_unacknowledged_filter(client):
    test_client, TestSession = client

    _, caregiver, _, alert_id = setup_alert(
        test_client,
        TestSession,
        "inbox3",
    )

    before = test_client.get(
        "/caregiver-alerts?unacknowledged_only=true",
        headers=caregiver["headers"],
    )

    assert before.status_code == 200
    assert len(before.json()) == 1

    acknowledged = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=caregiver["headers"],
    )

    assert acknowledged.status_code == 200

    after = test_client.get(
        "/caregiver-alerts?unacknowledged_only=true",
        headers=caregiver["headers"],
    )

    assert after.status_code == 200
    assert after.json() == []


def test_patient_cannot_access_caregiver_alerts(client):
    test_client, TestSession = client

    patient, _, _, _ = setup_alert(
        test_client,
        TestSession,
        "inbox4",
    )

    response = test_client.get(
        "/caregiver-alerts",
        headers=patient["headers"],
    )

    assert response.status_code == 403


def test_other_caregiver_cannot_acknowledge_alert(client):
    test_client, TestSession = client

    _, _, _, alert_id = setup_alert(
        test_client,
        TestSession,
        "inbox5",
    )

    outsider = register_caregiver(
        test_client,
        "inbox5outsider@example.com",
    )

    response = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=outsider["headers"],
    )

    assert response.status_code == 404


def test_revoked_caregiver_loses_alert_access(client):
    test_client, TestSession = client

    patient, caregiver, _, alert_id = setup_alert(
        test_client,
        TestSession,
        "inbox6",
    )

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    listed = test_client.get(
        "/caregiver-alerts",
        headers=caregiver["headers"],
    )

    assert listed.status_code == 200
    assert listed.json() == []

    acknowledged = test_client.patch(
        f"/caregiver-alerts/{alert_id}/acknowledge",
        headers=caregiver["headers"],
    )

    assert acknowledged.status_code == 404


def test_alert_api_requires_authentication(client):
    test_client, _ = client

    response = test_client.get("/caregiver-alerts")

    assert response.status_code == 401