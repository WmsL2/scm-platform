from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus


class SupplierContactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=64)

    @field_validator("contact_name", "contact_phone")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def requires_a_value(self) -> SupplierContactInput:
        if not (self.contact_name and self.contact_name.strip()) and not (
            self.contact_phone and self.contact_phone.strip()
        ):
            raise ValueError("A contact requires a name or phone")
        return self


class SupplierCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str = Field(min_length=1, max_length=255)
    main_brands: str = Field(min_length=1)
    advantage: str = Field(min_length=1)
    archive_status: ArchiveStatus = ArchiveStatus.DRAFT
    contacts: list[SupplierContactInput] = Field(default_factory=list, max_length=100)

    @field_validator("supplier_name", "main_brands", "advantage")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _normalize_required_text(value)


class SupplierUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str | None = Field(default=None, min_length=1, max_length=255)
    main_brands: str | None = Field(default=None, min_length=1)
    advantage: str | None = Field(default=None, min_length=1)
    archive_status: ArchiveStatus | None = None
    contacts: list[SupplierContactInput] | None = Field(default=None, max_length=100)

    @field_validator("supplier_name", "main_brands", "advantage")
    @classmethod
    def validate_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value)


class CooperationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)


class SupplierContactResponse(BaseModel):
    id: uuid.UUID
    contact_name: str | None
    contact_phone: str | None


class SupplierListItem(BaseModel):
    id: uuid.UUID
    supplier_code: str
    supplier_name: str
    main_brands: str
    advantage: str
    archive_status: ArchiveStatus
    cooperation_status: CooperationStatus


class SupplierDetailResponse(SupplierListItem):
    contacts: list[SupplierContactResponse]
    archived_by: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupplierDeleteResponse(BaseModel):
    id: uuid.UUID
    status: str = "deleted"


class SupplierImportRowResponse(BaseModel):
    source_row_number: int
    supplier_name: str | None
    main_brands: str | None
    advantage: str | None
    contact_name: str | None
    contact_phone: str | None
    is_valid: bool
    error_message: str | None


class SupplierImportPreviewResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[SupplierImportRowResponse]


class SupplierImportConfirmResponse(BaseModel):
    id: uuid.UUID
    status: str
    imported_count: int


class SupplierImportConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_status: ArchiveStatus = ArchiveStatus.ARCHIVED


def _normalize_required_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be blank")
    return normalized
