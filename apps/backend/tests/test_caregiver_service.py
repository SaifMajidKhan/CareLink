from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import User
from app.services.caregiver_service import (
    CaregiverAlreadyLinkedError,
    CaregiverLinkNotFoundError,
    CaregiverNotFoundError,
    caregiver_has_access,
    link_caregiver,
    list_patient_caregivers,
    revoke_caregiver,
)
from tests.test_registration import client


def create_user(test_client, email, caregiver=False):
    endpoint = (
        "/auth/register/caregiver"
        if caregiver
        else "/auth/register"
    )

    response = test_client.post(
        endpoint,
        json={
            "full_name": "CareLink Test User",
            "email": email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


def test_patient_can_link_caregiver(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "linkpatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "linkcaregiver@example.com", True
    )

    with TestSession() as db:
        relationship = link_caregiver(
            db, patient_id, "LINKCAREGIVER@example.com",
            "family",
        )

        assert relationship.caregiver_id == caregiver_id
        assert relationship.is_active is True
        assert relationship.relationship_type == "family"


def test_duplicate_link_rejected(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "duplicatepatient@example.com"
    )
    create_user(
        test_client, "duplicatecare@example.com", True
    )

    with TestSession() as db:
        link_caregiver(
            db, patient_id, "duplicatecare@example.com"
        )

        with pytest.raises(CaregiverAlreadyLinkedError):
            link_caregiver(
                db, patient_id, "duplicatecare@example.com"
            )


def test_non_caregiver_cannot_be_linked(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "patientone@example.com"
    )
    create_user(
        test_client, "patienttwo@example.com"
    )

    with TestSession() as db:
        with pytest.raises(CaregiverNotFoundError):
            link_caregiver(
                db, patient_id, "patienttwo@example.com"
            )


def test_unknown_caregiver_rejected(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "unknownpatient@example.com"
    )

    with TestSession() as db:
        with pytest.raises(CaregiverNotFoundError):
            link_caregiver(
                db, patient_id, "missing@example.com"
            )


def test_patient_can_list_active_caregivers(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "listpatient@example.com"
    )
    create_user(
        test_client, "listcare@example.com", True
    )

    with TestSession() as db:
        link_caregiver(
            db, patient_id, "listcare@example.com"
        )

        relationships = list_patient_caregivers(
            db, patient_id
        )

        assert len(relationships) == 1
        assert relationships[0].is_active is True


def test_revocation_removes_access(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "revokepatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "revokecare@example.com", True
    )

    with TestSession() as db:
        link_caregiver(
            db, patient_id, "revokecare@example.com"
        )

        assert caregiver_has_access(
            db, caregiver_id, patient_id
        )

        revoke_caregiver(
            db, patient_id, caregiver_id
        )

        assert not caregiver_has_access(
            db, caregiver_id, patient_id
        )

        assert list_patient_caregivers(
            db, patient_id
        ) == []


def test_revoked_link_can_be_reactivated(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "reactivatepatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "reactivatecare@example.com", True
    )

    with TestSession() as db:
        original = link_caregiver(
            db, patient_id, "reactivatecare@example.com"
        )

        original_id = original.id

        revoke_caregiver(
            db, patient_id, caregiver_id
        )

        restored = link_caregiver(
            db, patient_id, "reactivatecare@example.com"
        )

        assert restored.id == original_id
        assert restored.is_active is True
        assert caregiver_has_access(
            db, caregiver_id, patient_id
        )


def test_caregiver_cannot_access_unlinked_patient(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "isolatedpatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "isolatedcare@example.com", True
    )

    with TestSession() as db:
        assert not caregiver_has_access(
            db, caregiver_id, patient_id
        )


def test_revoking_missing_link_fails(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "missinglinkpatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "missinglinkcare@example.com", True
    )

    with TestSession() as db:
        with pytest.raises(CaregiverLinkNotFoundError):
            revoke_caregiver(
                db, patient_id, caregiver_id
            )


def test_inactive_caregiver_loses_access(client):
    test_client, TestSession = client

    patient_id = create_user(
        test_client, "inactivepatient@example.com"
    )
    caregiver_id = create_user(
        test_client, "inactivecare@example.com", True
    )

    with TestSession() as db:
        link_caregiver(
            db, patient_id, "inactivecare@example.com"
        )

        caregiver = db.get(User, caregiver_id)
        caregiver.is_active = False
        db.commit()

        assert not caregiver_has_access(
            db, caregiver_id, patient_id
        )