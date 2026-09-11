import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def create_token(
    user_id: uuid.UUID,
    version: int,
    session_id: uuid.UUID | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "ver": version,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_access_token_minutes),
    }
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(
        payload,
        settings.auth_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(token: str) -> tuple[uuid.UUID, int, uuid.UUID | None]:
    settings = get_settings()
    data = jwt.decode(
        token,
        settings.auth_jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        options={"require": ["sub", "ver", "iat", "exp"]},
    )
    raw_session_id = data.get("sid")
    session_id = uuid.UUID(raw_session_id) if raw_session_id is not None else None
    return uuid.UUID(data["sub"]), int(data["ver"]), session_id


def create_refresh_token(session_id: uuid.UUID) -> str:
    return f"{session_id}.{secrets.token_urlsafe(48)}"


def parse_refresh_token(token: str) -> uuid.UUID:
    session_id, secret = token.split(".", maxsplit=1)
    if not secret:
        raise ValueError("missing refresh token secret")
    return uuid.UUID(session_id)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_refresh_token(token), expected_hash)
