from tests.test_registration import client
from tests.test_medications import register_and_login


def register_caregiver(test_client, email):
    response = test_client.post(
        "/auth/register/caregiver",
        json={
            "full_name": "Caregiver API Test",
            "email": email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    login = test_client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "SecurePass123!",
        },
    )

    assert login.status_code == 200

    return {
        "id": response.json()["id"],
        "headers": {
            "Authorization": (
                f"Bearer {login.json()['access_token']}"
            )
        },
    }


def test_patient_can_link_and_list_caregiver(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "careapi1patient@example.com",
    )

    caregiver = register_caregiver(
        test_client,
        "careapi1caregiver@example.com",
    )

    response = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "careapi1caregiver@example.com",
            "relationship_type": "family",
        },
        headers=patient["headers"],
    )

    assert response.status_code == 201
    assert response.json()["caregiver_id"] == caregiver["id"]
    assert response.json()["is_active"] is True

    listed = test_client.get(
        "/caregivers",
        headers=patient["headers"],
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_duplicate_caregiver_link_returns_409(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "careapi2patient@example.com",
    )

    register_caregiver(
        test_client,
        "careapi2caregiver@example.com",
    )

    payload = {
        "caregiver_email": "careapi2caregiver@example.com",
    }

    first = test_client.post(
        "/caregivers",
        json=payload,
        headers=patient["headers"],
    )

    second = test_client.post(
        "/caregivers",
        json=payload,
        headers=patient["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_patient_can_revoke_caregiver(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "careapi3patient@example.com",
    )

    caregiver = register_caregiver(
        test_client,
        "careapi3caregiver@example.com",
    )

    linked = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "careapi3caregiver@example.com",
        },
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False

    listed = test_client.get(
        "/caregivers",
        headers=patient["headers"],
    )

    assert listed.json() == []


def test_caregiver_cannot_manage_patient_links(client):
    test_client, _ = client

    caregiver = register_caregiver(
        test_client,
        "careapi4caregiver@example.com",
    )

    response = test_client.get(
        "/caregivers",
        headers=caregiver["headers"],
    )

    assert response.status_code == 403

    response = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "careapi4caregiver@example.com",
        },
        headers=caregiver["headers"],
    )

    assert response.status_code == 403


def test_patient_cannot_revoke_another_patients_link(client):
    test_client, _ = client

    owner = register_and_login(
        test_client,
        "careapi5owner@example.com",
    )

    other = register_and_login(
        test_client,
        "careapi5other@example.com",
    )

    caregiver = register_caregiver(
        test_client,
        "careapi5caregiver@example.com",
    )

    linked = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "careapi5caregiver@example.com",
        },
        headers=owner["headers"],
    )

    assert linked.status_code == 201

    response = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=other["headers"],
    )

    assert response.status_code == 404

    owner_links = test_client.get(
        "/caregivers",
        headers=owner["headers"],
    )

    assert len(owner_links.json()) == 1


def test_caregiver_endpoints_require_authentication(client):
    test_client, _ = client

    response = test_client.get("/caregivers")

    assert response.status_code == 401


def test_invalid_caregiver_email_rejected(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "careapi7patient@example.com",
    )

    response = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "not-an-email",
        },
        headers=patient["headers"],
    )

    assert response.status_code == 422


def test_unknown_caregiver_returns_404(client):
    test_client, _ = client

    patient = register_and_login(
        test_client,
        "careapi8patient@example.com",
    )

    response = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": "unknowncaregiver@example.com",
        },
        headers=patient["headers"],
    )

    assert response.status_code == 404