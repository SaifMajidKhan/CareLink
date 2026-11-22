from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select

from app.models import CaregiverAlert
from app.services.alert_generation_service import (
    generate_patient_caregiver_alerts,
)
from tests.test_registration import client
from tests.test_caregiver_alert_api import setup_alert


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