import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.common.contracts import PageResult


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class UserRolesRequest(BaseModel):
    role_ids: list[uuid.UUID]


class RolePermissionsRequest(BaseModel):
    permission_ids: list[uuid.UUID]


class RoleCreateRequest(BaseModel):
    role_code: str = Field(min_length=1, max_length=64)
    role_name: str = Field(min_length=1, max_length=128)

    @field_validator("role_code")
    @classmethod
    def validate_role_code(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or not normalized.isascii()
            or not normalized[0].islower()
            or not normalized.replace("_", "").isalnum()
        ):
            raise ValueError("角色编码必须为小写英文、数字和下划线，且以小写英文开头")
        if normalized != normalized.lower():
            raise ValueError("角色编码必须为小写英文、数字和下划线，且以小写英文开头")
        return normalized

    @field_validator("role_name")
    @classmethod
    def validate_role_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("角色名称不能为空")
        return normalized


class ReviewRequest(BaseModel):
    review_note: str | None = Field(default=None, max_length=65535)


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    user_status: str
    role_ids: list[uuid.UUID]
    role_names: list[str]
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None


class RoleResponse(BaseModel):
    id: uuid.UUID
    role_code: str
    role_name: str
    permission_ids: list[uuid.UUID]


class PermissionResponse(BaseModel):
    id: uuid.UUID
    permission_code: str
    permission_name: str
    permission_type: str


RegistrationPage = PageResult[UserResponse]
