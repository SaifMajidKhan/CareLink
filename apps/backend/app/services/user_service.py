from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


def register_patient(db: Session, data: UserCreate) -> User:
    """Register a patient with a securely hashed password."""

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
        role=UserRole.PATIENT,
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