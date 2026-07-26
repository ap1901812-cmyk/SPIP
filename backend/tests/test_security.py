from __future__ import annotations

import pytest

from app.core.errors import UnauthenticatedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow() -> None:
    token = create_access_token(user_id=42, email="user@example.com", roles=["Planner"])
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"
    assert payload["roles"] == ["Planner"]
    assert "exp" in payload


def test_jwt_tampered_token_rejected() -> None:
    token = create_access_token(user_id=1, email="admin@example.com", roles=["Admin"])
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"

    with pytest.raises(UnauthenticatedError) as exc_info:
        decode_access_token(tampered_token)

    assert exc_info.value.code == "UNAUTHENTICATED"


def test_jwt_expired_token_rejected() -> None:
    token = create_access_token(
        user_id=1, email="user@example.com", roles=["Read-only"], expires_minutes=-10
    )

    with pytest.raises(UnauthenticatedError) as exc_info:
        decode_access_token(token)

    assert "expired" in exc_info.value.message.lower()
