import pytest
from openpyxl import Workbook

from app.common.contracts import AppError
from app.modules.type3_recommendation.application.service import Type3RecommendationService


def test_type3_output_columns_keep_physical_duplicate_header_positions() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["商品名称", "采购", "采购", None])

    columns = Type3RecommendationService._output_columns(sheet, 1)

    assert [(item.column_index, item.header, item.duplicate) for item in columns] == [
        (1, "商品名称", False),
        (2, "采购", True),
        (3, "采购", True),
    ]


def test_type3_output_mapping_rejects_unknown_field_and_invalid_column() -> None:
    with pytest.raises(AppError) as error:
        Type3RecommendationService._validate_output_mapping(
            {"version": 2, "columns": [{"column_index": 3, "field_key": "unknown"}]},
            max_column=2,
        )

    assert error.value.code == "TYPE3_EXPORT_MAPPING_INVALID"
