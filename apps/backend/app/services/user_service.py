from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


def register_user(
    db: Session,
    data: UserCreate,
    role: UserRole,
) -> User:
    """
    Register a patient or caregiver with a securely
    hashed password.

    Coordinator and administrator accounts cannot
    be created through public registration.
    """

    if role not in (
        UserRole.PATIENT,
        UserRole.CAREGIVER,
    ):
        raise ValueError(
            "Public registration is restricted to "
            "patient and caregiver accounts"
        )

    email = str(data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise EmailAlreadyRegisteredError()

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role=role,
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError()

    db.refresh(user)

    return user


def register_patient(
    db: Session,
    data: UserCreate,
) -> User:
    """Register a patient account."""

    return register_user(
        db=db,
        data=data,
        role=UserRole.PATIENT,
    )


def register_caregiver(
    db: Session,
    data: UserCreate,
) -> User:
    """Register a caregiver account."""

    return register_user(
        db=db,
        data=data,
        role=UserRole.CAREGIVER,
    )