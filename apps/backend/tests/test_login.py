import pytest
from uuid import UUID

from app.models import User
from tests.test_registration import client


@pytest.fixture
def registered_user(client):
    test_client, test_session = client

    response = test_client.post(
        "/auth/register",
        json={
            "full_name": "Login Test Patient",
            "email": "login@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201

    return test_client, test_session, response.json()["id"]


def login(test_client, password="SecurePassword123!"):
    return test_client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": password,
        },
    )


def test_login_success(registered_user):
    test_client, _, _ = registered_user

    response = login(test_client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_wrong_password_rejected(registered_user):
    test_client, _, _ = registered_user

    response = login(test_client, "WrongPassword123!")

    assert response.status_code == 401


def test_unknown_email_rejected(registered_user):
    test_client, _, _ = registered_user

    response = test_client.post(
        "/auth/login",
        data={
            "username": "unknown@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401


def test_me_requires_authentication(registered_user):
    test_client, _, _ = registered_user

    response = test_client.get("/auth/me")

    assert response.status_code == 401


def test_me_returns_authenticated_user(registered_user):
    test_client, _, user_id = registered_user

    token = login(test_client).json()["access_token"]

    response = test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["email"] == "login@example.com"
    assert "password_hash" not in response.json()


def test_invalid_token_rejected(registered_user):
    test_client, _, _ = registered_user

    response = test_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_disabled_user_cannot_login(registered_user):
    test_client, test_session, user_id = registered_user

    with test_session() as db:
        user = db.get(User, UUID(user_id))
        user.is_active = False
        db.commit()

    response = login(test_client)

    assert response.status_code == 401


def test_disabled_user_cannot_access_profile(registered_user):
    test_client, test_session, user_id = registered_user

    token = login(test_client).json()["access_token"]

    with test_session() as db:
        user = db.get(User, UUID(user_id))
        user.is_active = False
        db.commit()

    response = test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401