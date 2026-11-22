from uuid import UUID
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import AuditLog
from tests.test_registration import client
from tests.test_caregiver_api import register_caregiver
from tests.test_caregiver_dashboard import (
    setup_linked_accounts,
    adherence_url,
    risk_url,
)


def get_view_audits(db):
    return list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.action.in_(
                    [
                        "caregiver.adherence_viewed",
                        "caregiver.risk_viewed",
                    ]
                )
            )
        ).all()
    )


def test_adherence_view_creates_audit(client):
    test_client, TestSession = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client, "viewaudit1"
    )

    response = test_client.get(
        adherence_url(patient_id),
        headers=caregiver["headers"],
    )

    assert response.status_code == 200

    with TestSession() as db:
        audits = get_view_audits(db)

        assert len(audits) == 1
        assert audits[0].action == "caregiver.adherence_viewed"
        assert audits[0].actor_user_id == UUID(
            str(caregiver["id"])
        )
        assert audits[0].entity_id == patient_id
        assert audits[0].details == {
            "start_date": "2026-11-15",
            "end_date": "2026-11-17",
        }


def test_risk_view_creates_audit(client):
    test_client, TestSession = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client, "viewaudit2"
    )

    response = test_client.get(
        risk_url(patient_id),
        headers=caregiver["headers"],
    )

    assert response.status_code == 200

    with TestSession() as db:
        audits = get_view_audits(db)

        assert len(audits) == 1
        assert audits[0].action == "caregiver.risk_viewed"
        assert audits[0].actor_user_id == UUID(
            str(caregiver["id"])
        )
        assert audits[0].entity_id == patient_id
        assert audits[0].details == {}


def test_unlinked_caregiver_creates_no_view_audit(client):
    test_client, TestSession = client

    _, _, patient_id = setup_linked_accounts(
        test_client, "viewaudit3"
    )

    outsider = register_caregiver(
        test_client,
        "viewaudit3outsider@example.com",
    )

    response = test_client.get(
        risk_url(patient_id),
        headers=outsider["headers"],
    )

    assert response.status_code == 404

    with TestSession() as db:
        assert get_view_audits(db) == []


def test_revoked_caregiver_creates_no_new_view_audit(client):
    test_client, TestSession = client

    patient, caregiver, patient_id = setup_linked_accounts(
        test_client, "viewaudit4"
    )

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    response = test_client.get(
        risk_url(patient_id),
        headers=caregiver["headers"],
    )

    assert response.status_code == 404

    with TestSession() as db:
        assert get_view_audits(db) == []


def test_invalid_adherence_dates_create_no_view_audit(client):
    test_client, TestSession = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client, "viewaudit5"
    )

    response = test_client.get(
        f"/caregiver-dashboard/patients/{patient_id}/adherence"
        "?start_date=2026-11-18&end_date=2026-11-15",
        headers=caregiver["headers"],
    )

    assert response.status_code == 422

    with TestSession() as db:
        assert get_view_audits(db) == []


def test_audit_failure_prevents_successful_risk_response(client):
    test_client, TestSession = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client, "viewaudit6"
    )

    with patch(
        "app.api.caregiver_dashboard.record_audit_event",
        side_effect=RuntimeError("Simulated audit failure"),
    ):
        with pytest.raises(RuntimeError):
            test_client.get(
                risk_url(patient_id),
                headers=caregiver["headers"],
            )

    with TestSession() as db:
        assert get_view_audits(db) == []