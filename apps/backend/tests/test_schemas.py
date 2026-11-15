import pytest
from pydantic import ValidationError

from app.schemas import UserCreate, MedicationCreate
from app.models import UserRole


def test_valid_user_creation():
    user = UserCreate(
        full_name="Test Patient",
        email="patient@example.com",
        password="securepassword123",
    )

    assert user.full_name == "Test Patient"
    assert user.email == "patient@example.com"


def test_user_cannot_choose_own_role():
    with pytest.raises(ValidationError):
        UserCreate(
            full_name="Test Patient",
            email="patient@example.com",
            password="securepassword123",
            role=UserRole.ADMIN,
        )


def test_valid_medication_creation():
    medication = MedicationCreate(
        name="Metformin",
        dosage="500mg",
        condition="Diabetes",
        instructions="Take after meals",
        start_date="2026-11-10",
    )

    assert medication.name == "Metformin"
    assert medication.dosage == "500mg"


def test_medication_end_date_cannot_be_before_start_date():
    with pytest.raises(ValidationError):
        MedicationCreate(
            name="Metformin",
            dosage="500mg",
            condition="Diabetes",
            start_date="2026-11-10",
            end_date="2026-11-01",
        )