from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_adherence import (
    create_patient_medication_schedule,
    event_payload,
    event_url,
)


ANALYTICS_URL = (
    "/analytics/adherence"
    "?start_date=2026-11-15&end_date=2026-11-17"
)


def test_patient_gets_adherence_summary(client):
    test_client, _ = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "analytics1@example.com"
        )
    )

    recorded = test_client.post(
        event_url(medication_id, schedule_id),
        json=event_payload(),
        headers=patient["headers"],
    )
    assert recorded.status_code == 201

    response = test_client.get(
        ANALYTICS_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["expected"] == 3
    assert data["taken"] == 1
    assert data["missed"] == 0
    assert data["unrecorded"] == 2
    assert data["adherence_rate"] == 33.33


def test_patient_cannot_see_other_patients_analytics(client):
    test_client, _ = client

    create_patient_medication_schedule(
        test_client, "analyticsowner@example.com"
    )

    other = register_and_login(
        test_client, "analyticsother@example.com"
    )

    response = test_client.get(
        ANALYTICS_URL,
        headers=other["headers"],
    )

    assert response.status_code == 200
    assert response.json()["expected"] == 0
    assert response.json()["adherence_rate"] is None


def test_analytics_requires_authentication(client):
    test_client, _ = client

    response = test_client.get(ANALYTICS_URL)

    assert response.status_code == 401


def test_analytics_rejects_reversed_dates(client):
    test_client, _ = client

    patient = register_and_login(
        test_client, "analyticsdates@example.com"
    )

    response = test_client.get(
        "/analytics/adherence"
        "?start_date=2026-11-20&end_date=2026-11-15",
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_analytics_rejects_large_window(client):
    test_client, _ = client

    patient = register_and_login(
        test_client, "analyticswindow@example.com"
    )

    response = test_client.get(
        "/analytics/adherence"
        "?start_date=2026-01-01&end_date=2026-05-01",
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_inactive_medication_preserves_historical_counts(client):
    test_client, _ = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "analyticsinactive@example.com"
        )
    )

    deactivated = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )
    assert deactivated.status_code == 200

    response = test_client.get(
        ANALYTICS_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200
    assert response.json()["expected"] == 3

def test_deactivation_timestamps_are_saved(client):
    from datetime import timezone
    from uuid import UUID

    from app.models import Medication, MedicationSchedule

    test_client, TestSession = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client, "analyticslifecycle@example.com"
        )
    )

    response = test_client.patch(
        f"/medications/{medication_id}/deactivate",
        headers=patient["headers"],
    )

    assert response.status_code == 200

    with TestSession() as db:
        medication = db.get(Medication, UUID(medication_id))
        schedule = db.get(MedicationSchedule, UUID(schedule_id))

        assert medication.is_active is False
        assert schedule.is_active is False

        assert medication.deactivated_at is not None
        assert schedule.deactivated_at is not None

        assert (
            medication.deactivated_at
            == schedule.deactivated_at
        )

def test_analytics_excludes_doses_after_deactivation(client):
    from datetime import datetime, timezone
    from uuid import UUID

    from app.models import Medication, MedicationSchedule

    test_client, TestSession = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client,
            "analyticscutoff@example.com",
        )
    )

    # Simulate a medication deactivated on November 16
    # at 07:00 UTC, before its 08:00 scheduled dose.
    deactivation_time = datetime(
        2026, 11, 16, 7, 0, tzinfo=timezone.utc
    )

    with TestSession() as db:
        medication = db.get(Medication, UUID(medication_id))
        schedule = db.get(
            MedicationSchedule,
            UUID(schedule_id),
        )

        medication.is_active = False
        medication.deactivated_at = deactivation_time

        schedule.is_active = False
        schedule.deactivated_at = deactivation_time

        db.commit()

    response = test_client.get(
        ANALYTICS_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    # November 15: expected
    # November 16: excluded (deactivated before 08:00)
    # November 17: excluded
    assert data["expected"] == 1
    assert data["unrecorded"] == 1
    assert data["adherence_rate"] == 0.0

def test_repeated_deactivation_preserves_timestamp(client):
    from uuid import UUID

    from app.models import Medication, MedicationSchedule

    test_client, TestSession = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client,
            "analyticsrepeat@example.com",
        )
    )

    url = f"/medications/{medication_id}/deactivate"

    first = test_client.patch(
        url,
        headers=patient["headers"],
    )

    assert first.status_code == 200

    with TestSession() as db:
        medication = db.get(Medication, UUID(medication_id))
        original_timestamp = medication.deactivated_at

    assert original_timestamp is not None

    second = test_client.patch(
        url,
        headers=patient["headers"],
    )

    assert second.status_code == 200

    with TestSession() as db:
        medication = db.get(Medication, UUID(medication_id))
        schedule = db.get(
            MedicationSchedule,
            UUID(schedule_id),
        )

        assert medication.deactivated_at == original_timestamp
        assert schedule.deactivated_at == original_timestamp

def test_legacy_inactive_schedule_reports_warning(client):
    from uuid import UUID

    from app.models import Medication, MedicationSchedule

    test_client, TestSession = client

    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client,
            "analyticslegacy@example.com",
        )
    )

    with TestSession() as db:
        medication = db.get(Medication, UUID(medication_id))
        schedule = db.get(
            MedicationSchedule,
            UUID(schedule_id),
        )

        medication.is_active = False
        schedule.is_active = False

        medication.deactivated_at = None
        schedule.deactivated_at = None

        db.commit()

    response = test_client.get(
        ANALYTICS_URL,
        headers=patient["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["unknown_deactivation_schedules"] == 1
    assert data["historical_accuracy_warning"] is not None