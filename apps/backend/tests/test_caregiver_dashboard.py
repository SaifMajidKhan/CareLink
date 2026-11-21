from tests.test_registration import client
from tests.test_medications import register_and_login
from tests.test_caregiver_api import register_caregiver


def setup_linked_accounts(test_client, prefix):
    patient_email = f"{prefix}patient@example.com"
    caregiver_email = f"{prefix}caregiver@example.com"

    patient = register_and_login(
        test_client,
        patient_email,
    )

    caregiver = register_caregiver(
        test_client,
        caregiver_email,
    )

    patient_profile = test_client.get(
        "/auth/me",
        headers=patient["headers"],
    )

    assert patient_profile.status_code == 200

    patient_id = patient_profile.json()["id"]

    linked = test_client.post(
        "/caregivers",
        json={
            "caregiver_email": caregiver_email,
            "relationship_type": "family",
        },
        headers=patient["headers"],
    )

    assert linked.status_code == 201

    return patient, caregiver, patient_id


def adherence_url(patient_id):
    return (
        f"/caregiver-dashboard/patients/{patient_id}/adherence"
        "?start_date=2026-11-15&end_date=2026-11-17"
    )


def risk_url(patient_id):
    return (
        f"/caregiver-dashboard/patients/{patient_id}/risk"
    )


def test_linked_caregiver_can_view_adherence(client):
    test_client, _ = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client,
        "dashboard1",
    )

    response = test_client.get(
        adherence_url(patient_id),
        headers=caregiver["headers"],
    )

    assert response.status_code == 200
    assert "adherence_rate" in response.json()
    assert "expected" in response.json()


def test_linked_caregiver_can_view_risk(client):
    test_client, _ = client

    _, caregiver, patient_id = setup_linked_accounts(
        test_client,
        "dashboard2",
    )

    response = test_client.get(
        risk_url(patient_id),
        headers=caregiver["headers"],
    )

    assert response.status_code == 200
    assert "risk_level" in response.json()
    assert "reasons" in response.json()


def test_unlinked_caregiver_cannot_view_risk(client):
    test_client, _ = client

    _, _, patient_id = setup_linked_accounts(
        test_client,
        "dashboard3",
    )

    outsider = register_caregiver(
        test_client,
        "dashboard3outsider@example.com",
    )

    response = test_client.get(
        risk_url(patient_id),
        headers=outsider["headers"],
    )

    assert response.status_code == 404


def test_unlinked_caregiver_cannot_view_adherence(client):
    test_client, _ = client

    _, _, patient_id = setup_linked_accounts(
        test_client,
        "dashboard4",
    )

    outsider = register_caregiver(
        test_client,
        "dashboard4outsider@example.com",
    )

    response = test_client.get(
        adherence_url(patient_id),
        headers=outsider["headers"],
    )

    assert response.status_code == 404


def test_patient_cannot_use_caregiver_dashboard(client):
    test_client, _ = client

    patient, _, patient_id = setup_linked_accounts(
        test_client,
        "dashboard5",
    )

    response = test_client.get(
        risk_url(patient_id),
        headers=patient["headers"],
    )

    assert response.status_code == 403


def test_revoked_caregiver_loses_dashboard_access(client):
    test_client, _ = client

    patient, caregiver, patient_id = setup_linked_accounts(
        test_client,
        "dashboard6",
    )

    before = test_client.get(
        risk_url(patient_id),
        headers=caregiver["headers"],
    )

    assert before.status_code == 200

    revoked = test_client.delete(
        f"/caregivers/{caregiver['id']}",
        headers=patient["headers"],
    )

    assert revoked.status_code == 200

    after = test_client.get(
        risk_url(patient_id),
        headers=caregiver["headers"],
    )

    assert after.status_code == 404


def test_dashboard_requires_authentication(client):
    test_client, _ = client

    response = test_client.get(
        "/caregiver-dashboard/patients/"
        "00000000-0000-4000-8000-000000000001/risk"
    )

    assert response.status_code == 401


def test_caregiver_cannot_modify_patient_medications(client):
    test_client, _ = client

    _, caregiver, _ = setup_linked_accounts(
        test_client,
        "dashboard8",
    )

    response = test_client.post(
        "/medications",
        json={
            "name": "Test Medication",
            "dosage": "10 mg",
            "start_date": "2026-11-15",
        },
        headers=caregiver["headers"],
    )

    assert response.status_code == 403