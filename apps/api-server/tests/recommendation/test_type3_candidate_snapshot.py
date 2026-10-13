import json
import uuid
from datetime import date
from types import SimpleNamespace
from typing import cast

from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMN_KEYS
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.type3_recommendation.application.service import Type3RecommendationService


def test_type3_candidate_snapshot_serializes_product_date() -> None:
    values: dict[str, object] = {field: None for field in PRODUCT_EXPORT_COLUMN_KEYS}
    values.update(id=uuid.uuid4(), listed_at=date(2026, 10, 13))
    product = cast(Product, SimpleNamespace(**values))
    supplier = cast(
        Supplier,
        SimpleNamespace(id=uuid.uuid4(), supplier_name="测试供应商", supplier_code="SUP-TEST"),
    )

    candidate = Type3RecommendationService._candidate(
        uuid.uuid4(), "个护健康", 1, product, supplier
    )

    assert candidate.product_snapshot["listed_at"] == "2026-10-13"
    json.dumps(candidate.product_snapshot)
    json.dumps(candidate.price_snapshot)
