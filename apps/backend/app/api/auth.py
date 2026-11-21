from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.jwt_handler import create_access_token
from app.database import get_db
from app.models import User
from app.schemas.user import (
    UserCreate,
    UserRead,
    TokenResponse,
)
from app.services.auth_service import authenticate_user
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    register_patient,
    register_caregiver,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new patient."""

    try:
        return register_patient(db, data)

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


@router.post(
    "/register/caregiver",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_caregiver_account(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new caregiver."""

    try:
        return register_caregiver(db, data)

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""

    user = authenticate_user(
        db,
        email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserRead,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's profile."""

    return current_user