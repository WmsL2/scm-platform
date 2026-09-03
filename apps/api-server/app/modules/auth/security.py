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


def create_token(user_id: uuid.UUID, version: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "ver": version,
            "iat": now,
            "exp": now + timedelta(minutes=settings.auth_access_token_minutes),
        },
        settings.auth_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(token: str) -> tuple[uuid.UUID, int]:
    settings = get_settings()
    data = jwt.decode(
        token,
        settings.auth_jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        options={"require": ["sub", "ver", "iat", "exp"]},
    )
    return uuid.UUID(data["sub"]), int(data["ver"])
