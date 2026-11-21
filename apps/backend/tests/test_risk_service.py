from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models import (
    AdherenceEvent,
    AdherenceStatus,
    Medication,
    MedicationSchedule,
    User,
)
from app.services.risk_service import (
    get_patient_risk_assessment,
)
from tests.test_adherence import create_patient_medication_schedule
from tests.test_registration import client


AS_OF = datetime(
    2026, 11, 21, 12, tzinfo=timezone.utc
)


def setup_patient(test_client, email):
    patient, medication_id, schedule_id = (
        create_patient_medication_schedule(
            test_client,
            email,
        )
    )

    return patient, UUID(medication_id), UUID(schedule_id)


def test_risk_service_builds_expected_doses(client):
    test_client, TestSession = client

    patient, medication_id, schedule_id = setup_patient(
        test_client,
        "riskservice1@example.com",
    )

    with TestSession() as db:
        medication = db.get(Medication, medication_id)
        schedule = db.get(MedicationSchedule, schedule_id)

        medication.start_date = AS_OF.date() - timedelta(days=13)
        schedule.start_date = AS_OF.date() - timedelta(days=13)
        schedule.end_date = None

        db.commit()

        result = get_patient_risk_assessment(
            db,
            medication.patient_id,
            as_of=AS_OF,
        )

    assert result["metrics"]["expected"] == 14
    assert result["metrics"]["unrecorded"] == 14
    assert result["risk_level"] == "insufficient_data"


def test_risk_service_counts_recorded_doses(client):
    test_client, TestSession = client

    _, medication_id, schedule_id = setup_patient(
        test_client,
        "riskservice2@example.com",
    )

    with TestSession() as db:
        medication = db.get(Medication, medication_id)
        schedule = db.get(MedicationSchedule, schedule_id)

        medication.start_date = AS_OF.date() - timedelta(days=13)
        schedule.start_date = AS_OF.date() - timedelta(days=13)
        schedule.end_date = None

        for days_ago, status in [
            (3, AdherenceStatus.TAKEN),
            (2, AdherenceStatus.TAKEN),
            (1, AdherenceStatus.MISSED),
        ]:
            db.add(
                AdherenceEvent(
                    schedule_id=schedule_id,
                    recorded_by_user_id=medication.patient_id,
                    scheduled_for=(
                        AS_OF.replace(hour=8)
                        - timedelta(days=days_ago)
                    ),
                    status=status,
                )
            )

        db.commit()

        result = get_patient_risk_assessment(
            db,
            medication.patient_id,
            as_of=AS_OF,
        )

    assert result["metrics"]["expected"] == 14
    assert result["metrics"]["taken"] == 2
    assert result["metrics"]["missed"] == 1
    assert result["metrics"]["unrecorded"] == 11
    assert result["risk_level"] == "insufficient_data"


def test_risk_service_isolates_patients(client):
    test_client, TestSession = client

    _, first_medication_id, _ = setup_patient(
        test_client,
        "riskowner@example.com",
    )

    _, second_medication_id, _ = setup_patient(
        test_client,
        "riskother@example.com",
    )

    with TestSession() as db:
        first = db.get(Medication, first_medication_id)
        second = db.get(Medication, second_medication_id)

        first.start_date = AS_OF.date() - timedelta(days=13)
        second.start_date = AS_OF.date() - timedelta(days=13)

        first_schedule = first.schedules[0]
        second_schedule = second.schedules[0]

        first_schedule.start_date = first.start_date
        second_schedule.start_date = second.start_date

        first_schedule.end_date = None
        second_schedule.end_date = None

        db.commit()

        first_result = get_patient_risk_assessment(
            db,
            first.patient_id,
            as_of=AS_OF,
        )

        second_result = get_patient_risk_assessment(
            db,
            second.patient_id,
            as_of=AS_OF,
        )

    assert first_result["metrics"]["expected"] == 14
    assert second_result["metrics"]["expected"] == 14


def test_risk_service_empty_patient(client):
    test_client, TestSession = client

    from tests.test_medications import register_and_login

    patient = register_and_login(
        test_client,
        "riskempty@example.com",
    )

    with TestSession() as db:
        user = db.query(User).filter(
            User.email == "riskempty@example.com"
        ).one()

        result = get_patient_risk_assessment(
            db,
            user.id,
            as_of=AS_OF,
        )

    assert result["metrics"]["expected"] == 0
    assert result["risk_level"] == "insufficient_data"


def test_risk_service_excludes_doses_after_deactivation(client):
    test_client, TestSession = client

    _, medication_id, schedule_id = setup_patient(
        test_client,
        "riskdeactivated@example.com",
    )

    with TestSession() as db:
        medication = db.get(Medication, medication_id)
        schedule = db.get(MedicationSchedule, schedule_id)

        medication.start_date = AS_OF.date() - timedelta(days=3)
        schedule.start_date = AS_OF.date() - timedelta(days=3)
        schedule.end_date = None

        deactivated_at = (
            AS_OF.replace(hour=7)
            - timedelta(days=1)
        )

        medication.is_active = False
        medication.deactivated_at = deactivated_at

        schedule.is_active = False
        schedule.deactivated_at = deactivated_at

        db.commit()

        result = get_patient_risk_assessment(
            db,
            medication.patient_id,
            as_of=AS_OF,
        )

    assert result["metrics"]["expected"] == 2
    assert result["metrics"]["unrecorded"] == 2