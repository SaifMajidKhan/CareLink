from uuid import UUID

from app.models import User, UserRole
from tests.test_registration import client


def register_and_login(test_client, email):
    """Register a patient and return their JWT token."""

    registration = test_client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": email,
            "password": "SecurePassword123!",
        },
    )

    assert registration.status_code == 201

    login_response = test_client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "id": registration.json()["id"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


def medication_payload():
    return {
        "name": "Test Medication",
        "dosage": "1 tablet",
        "condition": "Test condition",
        "instructions": "Test instructions",
        "start_date": "2026-11-15",
        "end_date": None,
    }


def test_patient_can_create_medication(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "patient1@example.com"
    )

    response = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["patient_id"] == patient["id"]
    assert response.json()["name"] == "Test Medication"
    assert response.json()["is_active"] is True


def test_patient_can_list_own_medications(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "patient2@example.com"
    )

    test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    response = test_client.get(
        "/medications",
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patient_can_get_medication_by_id(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "patient3@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.get(
        f"/medications/{medication_id}",
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == medication_id


def test_unauthenticated_medication_creation_rejected(client):
    test_client, _ = client

    response = test_client.post(
        "/medications",
        json=medication_payload(),
    )

    assert response.status_code == 401


def test_unauthenticated_medication_list_rejected(client):
    test_client, _ = client

    response = test_client.get("/medications")

    assert response.status_code == 401


def test_invalid_medication_dates_rejected(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "patient4@example.com"
    )

    payload = medication_payload()
    payload["end_date"] = "2026-11-14"

    response = test_client.post(
        "/medications",
        json=payload,
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_patient_cannot_view_another_patients_medication(client):
    test_client, _ = client

    patient_a = register_and_login(
        test_client, "patienta@example.com"
    )
    patient_b = register_and_login(
        test_client, "patientb@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient_a["headers"],
    )

    assert created.status_code == 201

    medication_id = created.json()["id"]

    response = test_client.get(
        f"/medications/{medication_id}",
        headers=patient_b["headers"],
    )

    assert response.status_code == 404


def test_patient_cannot_list_another_patients_medications(client):
    test_client, _ = client

    patient_a = register_and_login(
        test_client, "owner@example.com"
    )
    patient_b = register_and_login(
        test_client, "other@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient_a["headers"],
    )

    assert created.status_code == 201

    response = test_client.get(
        "/medications",
        headers=patient_b["headers"],
    )

    assert response.status_code == 200
    assert response.json() == []


def test_non_patient_role_cannot_create_medication(client):
    test_client, test_session = client

    account = register_and_login(
        test_client, "caregiver@example.com"
    )

    with test_session() as db:
        user = db.get(User, UUID(account["id"]))
        user.role = UserRole.CAREGIVER
        db.commit()

    response = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=account["headers"],
    )

    assert response.status_code == 403

def test_patient_can_update_medication(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "update@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"dosage": "2 tablets"},
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["dosage"] == "2 tablets"
    assert response.json()["name"] == "Test Medication"


def test_patient_can_deactivate_medication(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "deactivate@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    fetched = test_client.get(
        f"/medications/{medication_id}",
        headers=patient["headers"],
    )

    assert fetched.status_code == 200
    assert fetched.json()["is_active"] is False


def test_patient_cannot_update_another_patients_medication(client):
    test_client, _ = client

    owner = register_and_login(
        test_client, "updateowner@example.com"
    )
    other = register_and_login(
        test_client, "updateother@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=owner["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"dosage": "5 tablets"},
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_patient_cannot_deactivate_another_patients_medication(client):
    test_client, _ = client

    owner = register_and_login(
        test_client, "deactivateowner@example.com"
    )
    other = register_and_login(
        test_client, "deactivateother@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=owner["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=other["headers"],
    )

    assert response.status_code == 404


def test_invalid_updated_dates_rejected(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "invalidupdate@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    medication_id = created.json()["id"]

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"end_date": "2026-11-14"},
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_inactive_medication_cannot_be_edited(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "inactiveupdate@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )

    medication_id = created.json()["id"]

    test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"dosage": "3 tablets"},
        headers=patient["headers"],
    )

    assert response.status_code == 409

def test_deactivation_also_deactivates_schedules(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "lifecycle1@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert created.status_code == 201

    medication_id = created.json()["id"]

    schedule = test_client.post(
        f"/medications/{medication_id}/schedules",
        json={
            "scheduled_time": "08:00:00",
            "days_of_week": [0, 2, 4],
            "start_date": "2026-11-15",
            "end_date": None,
        },
        headers=patient["headers"],
    )
    assert schedule.status_code == 201

    deactivated = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    schedules = test_client.get(
        f"/medications/{medication_id}/schedules",
        headers=patient["headers"],
    )

    assert schedules.status_code == 200
    assert len(schedules.json()) == 1
    assert schedules.json()[0]["is_active"] is False


def test_medication_start_date_cannot_invalidate_schedule(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "lifecycle2@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert created.status_code == 201

    medication_id = created.json()["id"]

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

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"start_date": "2026-11-18"},
        headers=patient["headers"],
    )

    assert response.status_code == 409


def test_medication_end_date_cannot_invalidate_schedule(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "lifecycle3@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert created.status_code == 201

    medication_id = created.json()["id"]

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

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"end_date": "2026-11-20"},
        headers=patient["headers"],
    )

    assert response.status_code == 409


def test_dosage_update_still_works_with_active_schedule(client):
    test_client, _ = client
    patient = register_and_login(
        test_client, "lifecycle4@example.com"
    )

    created = test_client.post(
        "/medications",
        json=medication_payload(),
        headers=patient["headers"],
    )
    assert created.status_code == 201

    medication_id = created.json()["id"]

    schedule = test_client.post(
        f"/medications/{medication_id}/schedules",
        json={
            "scheduled_time": "08:00:00",
            "days_of_week": [0, 2, 4],
            "start_date": "2026-11-15",
            "end_date": None,
        },
        headers=patient["headers"],
    )
    assert schedule.status_code == 201

    response = test_client.patch(
        f"/medications/{medication_id}",
        json={"dosage": "2 tablets"},
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["dosage"] == "2 tablets"