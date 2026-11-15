import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from dotenv import load_dotenv

load_dotenv()


def create_access_token(user_id: UUID) -> str:
    """Create a signed JWT access token."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    if algorithm != "HS256":
        raise RuntimeError("Unsupported JWT algorithm")

    expire_minutes = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    if expire_minutes <= 0:
        raise RuntimeError("Token expiration must be positive")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "type": "access",
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )


def decode_access_token(token: str) -> UUID:
    """Verify a JWT and return the authenticated user's ID."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={
                "require": ["sub", "iat", "exp"],
            },
        )

        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Invalid token type")

        return UUID(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise ValueError("Invalid or expired access token") from None