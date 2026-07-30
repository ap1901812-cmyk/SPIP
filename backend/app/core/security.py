from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import string
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.errors import UnauthenticatedError

settings = get_settings()

PBKDF2_ITERATIONS = 100_000


def validate_password_policy(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\\\/]", password):
        raise ValueError("Password must contain at least one special character.")


def generate_secure_temporary_password() -> str:
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*")
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    extra = "".join(secrets.choice(alphabet) for _ in range(6))
    chars = list(upper + lower + digit + special + extra)
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def hash_password(password: str) -> str:
    secret = get_settings().secret_key.encode()
    salt = hashlib.sha256(password.encode() + secret).digest()[:16]
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode(),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def _b64encode_url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def create_access_token(
    user_id: int,
    email: str,
    roles: list[str],
    expires_minutes: int | None = None,
) -> str:
    cfg = get_settings()
    minutes = expires_minutes if expires_minutes is not None else cfg.access_token_expire_minutes
    now = datetime.now(UTC)
    exp = int((now.timestamp()) + (minutes * 60))
    iat = int(now.timestamp())

    header = {"alg": cfg.jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "exp": exp,
        "iat": iat,
    }

    header_json = json.dumps(header, separators=(",", ":")).encode()
    payload_json = json.dumps(payload, separators=(",", ":")).encode()

    header_b64 = _b64encode_url(header_json)
    payload_b64 = _b64encode_url(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(
        cfg.secret_key.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode_url(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    cfg = get_settings()
    parts = token.split(".")
    if len(parts) != 3:
        raise UnauthenticatedError("Invalid token format.")

    header_b64, payload_b64, sig_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(
        cfg.secret_key.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    expected_sig_b64 = _b64encode_url(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise UnauthenticatedError("Invalid token signature.")

    try:
        header_bytes = base64.urlsafe_b64decode(header_b64 + "==")
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        header = json.loads(header_bytes)
        payload = json.loads(payload_bytes)
    except Exception as exc:
        raise UnauthenticatedError("Malformed token payload.") from exc

    if header.get("alg") != cfg.jwt_algorithm:
        raise UnauthenticatedError("Unsupported token algorithm.")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise UnauthenticatedError("Token missing expiration claim.")

    now_ts = datetime.now(UTC).timestamp()
    if now_ts > exp:
        raise UnauthenticatedError("Token has expired.")

    return payload
