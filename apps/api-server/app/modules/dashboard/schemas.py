from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    formal_product_count: int = Field(ge=0)
    archived_supplier_count: int = Field(ge=0)
