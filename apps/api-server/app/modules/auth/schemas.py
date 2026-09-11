import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    user_id: uuid.UUID
    username: str
    roles: list[str]
    role_names: dict[str, str]
    permissions: list[str]
    permission_names: dict[str, str]
    session_id: uuid.UUID | None = Field(default=None, exclude=True)
