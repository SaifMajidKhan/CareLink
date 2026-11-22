from datetime import datetime, timedelta, timezone

from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_caregiver_api import register_caregiver


EVALUATE_URL = "/analytics/risk/evaluate-alerts"
INBOX_URL = "/caregiver-alerts"


def setup_carelink_scenario(test_client, prefix):
    patient = register_and_login(
        test_client,
        f"{prefix}patient@example.com",
    )

    caregiver_email = f"{prefix}caregiver@example.com"

    caregiver = register_caregiver(
        test_client,
        caregiver_email,
    )

    linked = test_client.post(
        "/caregivers",
        json={"caregiver_email": caregiver_email},
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    # Use a recent schedule so this test remains valid
    # as the calendar date changes.
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=10)

    medication = test_client.post(
        "/medications",
        json={
            "name": "Integration Test Medication",
            "dosage": "1 tablet",
            "start_date": start_date.isoformat(),
        },
        headers=patient["headers"],
    )

    assert medication.status_code == 201
    medication_id = medication.json()["id"]

    schedule = test_client.post(
        f"/medications/{medication_id}/schedules",
        json={
            "scheduled_time": "08:00:00",
            "days_of_week": [],
            "start_date": start_date.isoformat(),
        },
        headers=patient["headers"],
    )

    assert schedule.status_code == 201
    schedule_id = schedule.json()["id"]

    return (
        patient,
        caregiver,
        medication_id,
        schedule_id,
        start_date,
    )


def record_missed_doses(
    test_client,
    patient,
    medication_id,
    schedule_id,
    start_date,
):
    event_url = (
        f"/medications/{medication_id}"
        f"/schedules/{schedule_id}/events"
    )

    # Record ten consecutive missed occurrences
    # sufficiently far in the past.
    for offset in range(10):
        dose_date = start_date + timedelta(days=offset)

        scheduled_for = datetime(
            dose_date.year,
            dose_date.month,
            dose_date.day,
            8,
            0,
            tzinfo=timezone.utc,
        )

        response = test_client.post(
            event_url,
            json={
                "scheduled_for": scheduled_for.isoformat(),
                "status": "missed",
                "notes": "Integration test missed dose",
            },
            headers=patient["headers"],
        )

        assert response.status_code == 201, response.text


def test_missed_doses_generate_caregiver_alert(client):
    test_client, _ = client

    (
        patient,
        caregiver,
        medication_id,
        schedule_id,
        start_date,
    ) = setup_carelink_scenario(
        test_client,
        "endtoend1",
    )

    record_missed_doses(
        test_client,
        patient,
        medication_id,
        schedule_id,
        start_date,
    )

    risk = test_client.get(
        "/analytics/risk",
        headers=patient["headers"],
    )

    assert risk.status_code == 200
    assert risk.json()["metrics"]["missed"] == 10

    evaluated = test_client.post(
        EVALUATE_URL,
        headers=patient["headers"],
    )

    assert evaluated.status_code == 200
    assert evaluated.json()["should_alert"] is True
    assert evaluated.json()["alerts_created"] == 1

    inbox = test_client.get(
        INBOX_URL,
        headers=caregiver["headers"],
    )

    assert inbox.status_code == 200
    assert len(inbox.json()) == 1

    alert = inbox.json()[0]

    assert alert["severity"] in ("medium", "high")
    assert alert["is_acknowledged"] is False

    acknowledged = test_client.patch(
        f"{INBOX_URL}/{alert['id']}/acknowledge",
        headers=caregiver["headers"],
    )

    assert acknowledged.status_code == 200
    assert acknowledged.json()["is_acknowledged"] is True


def test_repeated_real_evaluation_is_deduplicated(client):
    test_client, _ = client

    (
        patient,
        caregiver,
        medication_id,
        schedule_id,
        start_date,
    ) = setup_carelink_scenario(
        test_client,
        "endtoend2",
    )

    record_missed_doses(
        test_client,
        patient,
        medication_id,
        schedule_id,
        start_date,
    )

    first = test_client.post(
        EVALUATE_URL,
        headers=patient["headers"],
    )

    second = test_client.post(
        EVALUATE_URL,
        headers=patient["headers"],
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["alerts_created"] == 1
    assert second.json()["alerts_created"] == 0
    assert second.json()["alerts_existing"] == 1

    inbox = test_client.get(
        INBOX_URL,
        headers=caregiver["headers"],
    )

    assert inbox.status_code == 200
    assert len(inbox.json()) == 1