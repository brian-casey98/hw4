"""Password hashing and the signed login cookie.

Passwords are stored as pbkdf2_sha256$<salt>$<hex digest>. The salt is random
per account. The iteration count matches the seed user already in the database.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

PBKDF2_ITERATIONS = 120_000
COOKIE_NAME = "campus_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7
_SECRET_PATH = Path(__file__).resolve().parent / ".session_secret"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = _pbkdf2(password, salt)
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    check = _pbkdf2(password, salt)
    try:
        return hmac.compare_digest(check, digest)
    except ValueError:
        return False


def make_session_token(user_id: int) -> str:
    payload = _encode(
        json.dumps({"uid": user_id, "exp": int(time.time()) + COOKIE_MAX_AGE}).encode()
    )
    signature = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session_token(token: str) -> int | None:
    try:
        payload, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).hexdigest()
    try:
        if not hmac.compare_digest(expected, signature):
            return None
    except ValueError:
        return None
    try:
        data = json.loads(_decode(payload))
        if int(data["exp"]) < time.time():
            return None
        return int(data["uid"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _pbkdf2(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        PBKDF2_ITERATIONS,
    )
    return digest.hex()


def _session_secret() -> bytes:
    if _SECRET_PATH.exists():
        secret = _SECRET_PATH.read_text(encoding="utf-8").strip()
        if secret:
            return secret.encode()
    secret = secrets.token_hex(32)
    _SECRET_PATH.write_text(secret, encoding="utf-8")
    return secret.encode()


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
