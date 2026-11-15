from tests.test_registration import client
from tests.test_medications import (
    register_and_login,
    medication_payload,
)


def create_patient_and_medication(test_client, email):
    """Create a patient and one active medication."""

    patient = register_and_login(test_client, email)

    response = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 201

    return patient, response.json()["id"]


def schedule_payload():
    return {
        "scheduled_time": "08:00:00",
        "days_of_week": [0, 2, 4],
        "start_date": "2026-11-15",
        "end_date": None,
    }


def test_patient_can_create_schedule(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "schedule1@example.com"
    )

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=schedule_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["medication_id"] == medication_id
    assert response.json()["days_of_week"] == [0, 2, 4]
    assert response.json()["is_active"] is True


def test_patient_can_list_schedules(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "schedule2@example.com"
    )

    created = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=schedule_payload(),
        headers=patient["headers"],
    )

    assert created.status_code == 201

    response = test_client.get(
        f"/medications/{medication_id}/schedules",
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == created.json()["id"]


def test_unauthenticated_schedule_creation_rejected(client):
    test_client, _ = client

    response = test_client.post(
        "/medications/00000000-0000-0000-0000-000000000001/schedules",
        json=schedule_payload(),
    )

    assert response.status_code == 401


def test_unauthenticated_schedule_listing_rejected(client):
    test_client, _ = client

    response = test_client.get(
        "/medications/00000000-0000-0000-0000-000000000001/schedules"
    )

    assert response.status_code == 401


def test_patient_cannot_create_schedule_for_another_patient(client):
    test_client, _ = client

    owner, medication_id = create_patient_and_medication(
        test_client, "scheduleowner@example.com"
    )

    other = register_and_login(
        test_client, "scheduleother@example.com"
    )

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=schedule_payload(),
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_patient_cannot_list_another_patients_schedules(client):
    test_client, _ = client

    owner, medication_id = create_patient_and_medication(
        test_client, "schedulelistowner@example.com"
    )

    other = register_and_login(
        test_client, "schedulelistother@example.com"
    )

    response = test_client.get(
        f"/medications/{medication_id}/schedules",
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_inactive_medication_cannot_receive_schedule(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "scheduleinactive@example.com"
    )

    deactivated = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )

    assert deactivated.status_code == 200

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=schedule_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 409


def test_invalid_weekday_rejected(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "scheduleweekday@example.com"
    )

    payload = schedule_payload()
    payload["days_of_week"] = [0, 7]

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_duplicate_weekdays_rejected(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "scheduleduplicate@example.com"
    )

    payload = schedule_payload()
    payload["days_of_week"] = [0, 0, 2]

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_schedule_cannot_start_before_medication(client):
    test_client, _ = client

    patient, medication_id = create_patient_and_medication(
        test_client, "scheduleearly@example.com"
    )

    payload = schedule_payload()
    payload["start_date"] = "2026-11-14"

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_schedule_cannot_start_after_medication_ends(client):
    test_client, _ = client

    patient = register_and_login(
        test_client, "schedulelate@example.com"
    )

    medication_data = medication_payload()
    medication_data["end_date"] = "2026-11-20"

    created = test_client.post(
        "/medications",
        json=medication_data,
        headers=patient["headers"],
    )

    assert created.status_code == 201

    medication_id = created.json()["id"]

    payload = schedule_payload()
    payload["start_date"] = "2026-11-21"
    payload["end_date"] = "2026-11-22"

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_schedule_cannot_extend_beyond_medication_end(client):
    test_client, _ = client

    patient = register_and_login(
        test_client, "scheduleend@example.com"
    )

    medication_data = medication_payload()
    medication_data["end_date"] = "2026-11-20"

    created = test_client.post(
        "/medications",
        json=medication_data,
        headers=patient["headers"],
    )

    assert created.status_code == 201

    medication_id = created.json()["id"]

    payload = schedule_payload()
    payload["end_date"] = "2026-11-25"

    response = test_client.post(
        f"/medications/{medication_id}/schedules",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422