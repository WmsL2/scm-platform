import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DashboardRecentProjectResponse(BaseModel):
    id: uuid.UUID
    project_code: str
    project_name: str
    project_type: str
    status: str
    updated_at: datetime


class DashboardSummaryResponse(BaseModel):
    formal_product_count: int = Field(ge=0)
    normal_supplier_count: int = Field(ge=0)
    active_project_count: int = Field(ge=0)
    pending_supplier_count: int = Field(ge=0)
    recent_projects: list[DashboardRecentProjectResponse]
