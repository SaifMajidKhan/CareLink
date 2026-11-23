from sqlalchemy import select

from app.models import CaregiverAlert
from app.services.alert_service import create_caregiver_alert
from tests.test_registration import client
from tests.test_alert_service import (
    setup_accounts,
    sample_assessment,
)


def test_uncommitted_duplicate_alert_is_reused(client):
    test_client, TestSession = client

    with TestSession() as db:
        patient_id, caregiver_id = setup_accounts(
            test_client,
            db,
            "dedup1",
        )

        arguments = {
            "db": db,
            "patient_id": patient_id,
            "caregiver_id": caregiver_id,
            "assessment": sample_assessment(),
            "severity": "high",
            "title": "High adherence risk",
            "message": "Repeated missed doses",
            "commit": False,
        }

        first = create_caregiver_alert(**arguments)
        second = create_caregiver_alert(**arguments)

        assert first.id == second.id

        db.commit()

    with TestSession() as db:
        alerts = db.scalars(
            select(CaregiverAlert).where(
                CaregiverAlert.patient_id == patient_id,
                CaregiverAlert.caregiver_id == caregiver_id,
            )
        ).all()

        assert len(alerts) == 1