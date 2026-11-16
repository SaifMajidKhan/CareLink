from tests.test_registration import client
from tests.test_medications import (
    medication_payload,
    register_and_login,
)


def create_patient_medication_schedule(test_client, email):
    patient = register_and_login(test_client, email)

    medication = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert medication.status_code == 201

    medication_id = medication.json()["id"]

    schedule = test_client.post(
        f"/medications/{medication_id}/schedules",
        json={
            "scheduled_time": "08:00:00",
            "days_of_week": [],
            "start_date": "2026-11-15",
            "end_date": None,
        },
        headers=patient["headers"],
    )
    assert schedule.status_code == 201

    return patient, medication_id, schedule.json()["id"]


def event_payload():
    return {
        "scheduled_for": "2026-11-15T08:00:00Z",
        "status": "taken",
        "notes": "Taken as scheduled",
    }


def event_url(medication_id, schedule_id):
    return (
        f"/medications/{medication_id}"
        f"/schedules/{schedule_id}/events"
    )


def test_patient_can_record_taken_dose(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence1@example.com"
        )
    )

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=event_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["status"] == "taken"
    assert response.json()["schedule_id"] == schedule_id
    assert response.json()["recorded_by_user_id"] == patient["id"]


def test_patient_can_view_dose_history(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence2@example.com"
        )
    )

    url = event_url(medication_id, schedule_id)

    created = test_client.post(
        url,
        json=event_payload(),
        headers=patient["headers"],
    )
    assert created.status_code == 201

    response = test_client.get(
        url, headers=patient["headers"]
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == created.json()["id"]


def test_duplicate_dose_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence3@example.com"
        )
    )

    url = event_url(medication_id, schedule_id)

    first = test_client.post(
        url, json=event_payload(),
        headers=patient["headers"],
    )
    second = test_client.post(
        url, json=event_payload(),
        headers=patient["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_patient_cannot_record_another_patients_dose(client):
    test_client, _ = client
    owner, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherenceowner@example.com"
        )
    )
    other = register_and_login(
        test_client, "adherenceother@example.com"
    )

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=event_payload(),
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_patient_cannot_view_another_patients_events(client):
    test_client, _ = client
    owner, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherenceowner2@example.com"
        )
    )
    other = register_and_login(
        test_client, "adherenceother2@example.com"
    )

    response = test_client.get(
        event_url(medication_id, schedule_id),
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_unauthenticated_dose_recording_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence4@example.com"
        )
    )

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=event_payload(),
    )

    assert response.status_code == 401


def test_future_dose_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence5@example.com"
        )
    )

    payload = event_payload()
    payload["scheduled_for"] = "2099-11-15T08:00:00Z"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_wrong_scheduled_time_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence6@example.com"
        )
    )

    payload = event_payload()
    payload["scheduled_for"] = "2026-11-15T09:00:00Z"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_dose_before_schedule_start_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence7@example.com"
        )
    )

    payload = event_payload()
    payload["scheduled_for"] = "2026-11-14T08:00:00Z"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_inactive_schedule_rejects_new_dose(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence8@example.com"
        )
    )

    deactivated = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )
    assert deactivated.status_code == 200

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=event_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 409


def test_unknown_status_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence9@example.com"
        )
    )

    payload = event_payload()
    payload["status"] = "unknown"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_timestamp_without_timezone_rejected(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence10@example.com"
        )
    )

    payload = event_payload()
    payload["scheduled_for"] = "2026-11-15T08:00:00"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_timezone_offset_is_converted_to_utc(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence11@example.com"
        )
    )

    payload = event_payload()
    payload["scheduled_for"] = "2026-11-15T13:00:00+05:00"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["status"] == "taken"


def test_missed_dose_can_be_recorded(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence12@example.com"
        )
    )

    payload = event_payload()
    payload["status"] = "missed"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["status"] == "missed"


def test_skipped_dose_can_be_recorded(client):
    test_client, _ = client
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "adherence13@example.com"
        )
    )

    payload = event_payload()
    payload["status"] = "skipped"

    response = test_client.post(
        event_url(medication_id, schedule_id),
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["status"] == "skipped"


def test_dose_on_unscheduled_weekday_rejected(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "adherence14@example.com"
    )

    medication = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert medication.status_code == 201
    medication_id = medication.json()["id"]

    schedule = test_client.post(
        f"/medications/{medication_id}/schedules",
        json={
            "scheduled_time": "08:00:00",
            "days_of_week": [0],
            "start_date": "2026-11-15",
            "end_date": None,
        },
        headers=patient["headers"],
    )
    assert schedule.status_code == 201

    response = test_client.post(
        event_url(medication_id, schedule.json()["id"]),
        json=event_payload(),
        headers=patient["headers"],
    )

    # November 15, 2026 is Sunday, not Monday.
    assert response.status_code == 422