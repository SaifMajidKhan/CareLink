from uuid import uuid4

import jwt
import pytest

from app.core.jwt_handler import (
    create_access_token,
    decode_access_token,
)


@pytest.fixture(autouse=True)
def configure_test_secret(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-not-for-production",
    )
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")


def test_access_token_creation_and_decoding():
    user_id = uuid4()

    token = create_access_token(user_id)

    assert isinstance(token, str)
    assert decode_access_token(token) == user_id


def test_invalid_token_rejected():
    with pytest.raises(ValueError):
        decode_access_token("invalid.token.value")


def test_tampered_token_rejected():
    token = create_access_token(uuid4())

    tampered = token[:-1] + (
        "A" if token[-1] != "A" else "B"
    )

    with pytest.raises(ValueError):
        decode_access_token(tampered)


def test_expired_token_rejected(monkeypatch):
    user_id = uuid4()

    monkeypatch.setenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "1",
    )

    token = create_access_token(user_id)

    # Verify that a token signed with an expired timestamp is rejected.
    from datetime import datetime, timedelta, timezone

    expired_payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "type": "access",
    }

    expired_token = jwt.encode(
        expired_payload,
        "test-secret-key-not-for-production",
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        decode_access_token(expired_token)


def test_missing_secret_rejected(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY")

    with pytest.raises(RuntimeError):
        create_access_token(uuid4())