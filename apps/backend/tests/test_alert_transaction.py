from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import AuditLog, CaregiverAlert
from tests.test_registration import client
from tests.test_alert_evaluation_api import (
    ENDPOINT,
    sample_risk,
    setup_patient_and_caregiver,
)


def test_audit_failure_rolls_back_generated_alerts(client):
    test_client, TestSession = client

    patient, _ = setup_patient_and_caregiver(
        test_client, "transaction1"
    )

    with (
        patch(
            "app.services.alert_generation_service.get_patient_risk_assessment",
            return_value=sample_risk(),
        ),
        patch(
            "app.api.analytics.record_audit_event",
            side_effect=RuntimeError("Audit failure"),
        ),
    ):
        with pytest.raises(RuntimeError):
            test_client.post(
                ENDPOINT,
                headers=patient["headers"],
            )

    with TestSession() as db:
        alerts = db.scalars(select(CaregiverAlert)).all()

        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action
                == "patient.risk_alerts_evaluated"
            )
        ).all()

        assert alerts == []
        assert audits == []


def test_successful_evaluation_commits_alert_and_audit(client):
    test_client, TestSession = client

    patient, _ = setup_patient_and_caregiver(
        test_client, "transaction2"
    )

    with patch(
        "app.services.alert_generation_service.get_patient_risk_assessment",
        return_value=sample_risk(),
    ):
        response = test_client.post(
            ENDPOINT,
            headers=patient["headers"],
        )

    assert response.status_code == 200
    assert response.json()["alerts_created"] == 1

    with TestSession() as db:
        alerts = db.scalars(select(CaregiverAlert)).all()

        audits = db.scalars(
            select(AuditLog).where(
                AuditLog.action
                == "patient.risk_alerts_evaluated"
            )
        ).all()

        assert len(alerts) == 1
        assert len(audits) == 1