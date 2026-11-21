from sqlalchemy import select

from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.services.user_service import register_user
from tests.test_registration import client


def caregiver_payload(
    email="caregiver@example.com",
):
    return {
        "full_name": "Test Caregiver",
        "email": email,
        "password": "SecurePass123!",
    }


def test_caregiver_registration(client):
    test_client, _ = client

    response = test_client.post(
        "/auth/register/caregiver",
        json=caregiver_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["role"] == "caregiver"
    assert data["email"] == "caregiver@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_caregiver_can_login(client):
    test_client, _ = client

    test_client.post(
        "/auth/register/caregiver",
        json=caregiver_payload(
            "caregiverlogin@example.com"
        ),
    )

    response = test_client.post(
        "/auth/login",
        data={
            "username": "caregiverlogin@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_duplicate_caregiver_email_rejected(client):
    test_client, _ = client

    payload = caregiver_payload(
        "duplicatecaregiver@example.com"
    )

    first = test_client.post(
        "/auth/register/caregiver",
        json=payload,
    )

    second = test_client.post(
        "/auth/register/caregiver",
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_patient_and_caregiver_cannot_share_email(client):
    test_client, _ = client

    payload = caregiver_payload(
        "sharedemail@example.com"
    )

    patient = test_client.post(
        "/auth/register",
        json=payload,
    )

    caregiver = test_client.post(
        "/auth/register/caregiver",
        json=payload,
    )

    assert patient.status_code == 201
    assert caregiver.status_code == 409


def test_caregiver_cannot_use_patient_medication_api(client):
    test_client, _ = client

    test_client.post(
        "/auth/register/caregiver",
        json=caregiver_payload(
            "caregiverrestricted@example.com"
        ),
    )

    login = test_client.post(
        "/auth/login",
        data={
            "username": "caregiverrestricted@example.com",
            "password": "SecurePass123!",
        },
    )

    token = login.json()["access_token"]

    response = test_client.get(
        "/medications",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403


def test_public_registration_cannot_create_admin(client):
    _, TestSession = client

    with TestSession() as db:
        data = UserCreate(
            **caregiver_payload(
                "adminblocked@example.com"
            )
        )

        try:
            register_user(
                db,
                data,
                UserRole.ADMIN,
            )
            assert False, "Admin registration must fail"
        except ValueError:
            pass

        user = db.scalar(
            select(User).where(
                User.email == "adminblocked@example.com"
            )
        )

        assert user is None


def test_caregiver_password_is_hashed(client):
    test_client, TestSession = client

    response = test_client.post(
        "/auth/register/caregiver",
        json=caregiver_payload(
            "caregiverhash@example.com"
        ),
    )

    assert response.status_code == 201

    with TestSession() as db:
        user = db.scalar(
            select(User).where(
                User.email == "caregiverhash@example.com"
            )
        )

        assert user is not None
        assert user.password_hash != "SecurePass123!"
        assert user.password_hash.startswith("$argon2")