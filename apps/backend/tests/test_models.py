from sqlalchemy import create_engine, inspect

from app.models import Base


def test_all_core_tables_exist():
    """Check that all six CareLink tables are registered."""

    expected_tables = {
        "users",
        "patient_caregivers",
        "medications",
        "medication_schedules",
        "adherence_events",
        "audit_logs",
    }

    actual_tables = set(Base.metadata.tables.keys())

    assert expected_tables.issubset(actual_tables)


def test_tables_can_be_created_in_test_database():
    """Check that our models can create tables in a temporary database."""

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())

    expected_tables = {
        "users",
        "patient_caregivers",
        "medications",
        "medication_schedules",
        "adherence_events",
        "audit_logs",
    }

    assert expected_tables.issubset(actual_tables)

    engine.dispose()


def test_users_table_has_required_columns():
    """Check that the users table contains its essential fields."""

    users_table = Base.metadata.tables["users"]

    expected_columns = {
        "id",
        "full_name",
        "email",
        "password_hash",
        "role",
        "is_active",
    }

    actual_columns = set(users_table.columns.keys())

    assert expected_columns.issubset(actual_columns)