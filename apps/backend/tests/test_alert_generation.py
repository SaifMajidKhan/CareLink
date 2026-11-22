from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select

from app.models import CaregiverAlert
from app.services.alert_generation_service import (
    generate_patient_caregiver_alerts,
)
from tests.test_registration import client
from tests.test_caregiver_alert_api import setup_alert
from tests.test_caregiver_api import register_caregiver


def risk_assessment(level="high", score=80):
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


def test_high_risk_generates_caregiver_alert(client):
    test_client, TestSession = client

    _, caregiver, patient_id, _ = setup_alert(
        test_client, TestSession, "generation1"
    )

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=risk_assessment(score=85),
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["should_alert"] is True
        assert result["alerts_created"] == 1

        alerts = db.scalars(
            select(CaregiverAlert).where(
                CaregiverAlert.caregiver_id == UUID(
                    str(caregiver["id"])
                ),
                CaregiverAlert.risk_score == 85,
            )
        ).all()

        assert len(alerts) == 1


def test_repeated_generation_does_not_duplicate(client):
    test_client, TestSession = client

    _, _, patient_id, _ = setup_alert(
        test_client, TestSession, "generation2"
    )

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=risk_assessment(score=90),
        ):
            first = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )
            second = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert first["alerts_created"] == 1
        assert second["alerts_created"] == 0
        assert second["alerts_existing"] == 1


def test_low_risk_does_not_generate_alert(client):
    test_client, TestSession = client

    _, _, patient_id, _ = setup_alert(
        test_client, TestSession, "generation3"
    )

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=risk_assessment("low", 10),
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["should_alert"] is False
        assert result["alerts_created"] == 0

def test_multiple_caregivers_receive_separate_alerts(client):
    test_client, TestSession = client

    patient, first_caregiver, patient_id, _ = setup_alert(
        test_client, TestSession, "generation4"
    )

    second_email = "generation4second@example.com"

    second_caregiver = register_caregiver(
        test_client,
        second_email,
    )

    linked = test_client.post(
        "/caregivers",
        json={"caregiver_email": second_email},
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=risk_assessment(score=95),
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["alerts_created"] == 2
        assert result["caregivers_processed"] == 2

        alerts = db.scalars(
            select(CaregiverAlert).where(
                CaregiverAlert.patient_id == UUID(patient_id),
                CaregiverAlert.risk_score == 95,
            )
        ).all()

        assert len(alerts) == 2
        assert {alert.caregiver_id for alert in alerts} == {
            UUID(str(first_caregiver["id"])),
            UUID(str(second_caregiver["id"])),
        }


def test_revoked_caregiver_does_not_receive_new_alert(client):
    test_client, TestSession = client

    patient, caregiver, patient_id, _ = setup_alert(
        test_client, TestSession, "generation5"
    )

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=risk_assessment(score=95),
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["alerts_created"] == 0
        assert result["caregivers_processed"] == 0

        new_alerts = db.scalars(
            select(CaregiverAlert).where(
                CaregiverAlert.patient_id == UUID(patient_id),
                CaregiverAlert.risk_score == 95,
            )
        ).all()

        assert len(new_alerts) == 0


def test_insufficient_data_does_not_generate_alert(client):
    test_client, TestSession = client

    _, _, patient_id, _ = setup_alert(
        test_client, TestSession, "generation6"
    )

    assessment = {
        "risk_level": "insufficient_data",
        "risk_score": None,
        "confidence": "low",
        "trend": "insufficient_data",
        "metrics": {
            "expected": 0,
            "recorded": 0,
        },
        "reasons": ["No expected doses available"],
    }

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=assessment,
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["should_alert"] is False
        assert result["alerts_created"] == 0


def test_existing_alert_is_not_duplicated(client):
    test_client, TestSession = client

    _, caregiver, patient_id, _ = setup_alert(
        test_client, TestSession, "generation7"
    )

    # setup_alert already stores an alert with this assessment.
    existing_assessment = {
        "risk_level": "high",
        "risk_score": 80,
        "confidence": "high",
        "trend": "declining",
        "metrics": {
            "expected": 10,
            "missed": 6,
        },
        "reasons": ["Repeated missed doses"],
    }

    with TestSession() as db:
        with patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=existing_assessment,
        ):
            result = generate_patient_caregiver_alerts(
                db, UUID(patient_id)
            )

        assert result["alerts_created"] == 0
        assert result["alerts_existing"] == 1

        alerts = db.scalars(
            select(CaregiverAlert).where(
                CaregiverAlert.caregiver_id
                == UUID(str(caregiver["id"]))
            )
        ).all()

        assert len(alerts) == 1