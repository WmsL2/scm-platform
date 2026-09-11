import uuid

import jwt
import pytest

from app.modules.auth.security import create_token, decode_token, hash_password, verify_password


def test_argon2id_password_hash() -> None:
    hashed = hash_password("correct-password")
    assert hashed != "correct-password"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_minimal_payload() -> None:
    session_id = uuid.uuid4()
    token = create_token(uuid.uuid4(), 1, session_id)
    payload = jwt.decode(token, options={"verify_signature": False})
    assert {"sub", "ver", "sid", "jti", "iat", "exp"} <= payload.keys()
    assert not {"roles", "permissions", "password", "supplier"} & payload.keys()
    assert decode_token(token)[1] == 1
    assert decode_token(token)[2] == session_id


@pytest.mark.parametrize(
    "token",
    [
        "invalid",
        jwt.encode(
            {"sub": "not-uuid", "ver": 1},
            "wrong-signature-test-secret-at-least-32-bytes",
            algorithm="HS256",
        ),
    ],
)
def test_invalid_tokens_raise(token: str) -> None:
    with pytest.raises(Exception):
        decode_token(token)
