from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus


class SupplierContactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=64)

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
    contacts: list[SupplierContactInput] = Field(default_factory=list, max_length=100)


class SupplierUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str | None = Field(default=None, min_length=1, max_length=255)
    main_brands: str | None = Field(default=None, min_length=1)
    advantage: str | None = Field(default=None, min_length=1)
    contacts: list[SupplierContactInput] | None = Field(default=None, max_length=100)


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
