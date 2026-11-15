import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, User, UserRole


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client, TestSession
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_patient_registration(client):
    test_client, test_session = client

    response = test_client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": "patient@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "patient@example.com"
    assert data["role"] == "patient"
    assert "password" not in data
    assert "password_hash" not in data

    with test_session() as db:
        user = db.scalar(
            select(User).where(
                User.email == "patient@example.com"
            )
        )

        assert user is not None
        assert user.role == UserRole.PATIENT
        assert user.password_hash != "SecurePassword123!"


def test_duplicate_email_rejected(client):
    test_client, _ = client

    payload = {
        "full_name": "Test Patient",
        "email": "patient@example.com",
        "password": "SecurePassword123!",
    }

    first = test_client.post("/auth/register", json=payload)
    second = test_client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_email_rejected(client):
    test_client, _ = client

    response = test_client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": "invalid-email",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 422


def test_registration_cannot_assign_admin_role(client):
    test_client, _ = client

    response = test_client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": "patient@example.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )

    assert response.status_code == 422