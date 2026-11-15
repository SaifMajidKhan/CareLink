from app.core.security import hash_password, verify_password


def test_password_hash_is_not_plaintext():
    password = "SecurePassword123!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_correct_password_verification():
    password = "SecurePassword123!"

    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_wrong_password_rejected():
    hashed = hash_password("CorrectPassword123!")

    assert verify_password("WrongPassword123!", hashed) is False


def test_same_password_produces_different_hashes():
    password = "SecurePassword123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash