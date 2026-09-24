from io import BytesIO

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.common.contracts import AppError
from app.modules.recommendation.template.analyzer import (
    analyze_template,
    inspect_template_structure,
    validate_mapping_contract,
)
from app.modules.recommendation.template.schemas import RecommendationTemplateMappingUpdateRequest


def _workbook_bytes(headers: list[str]) -> bytes:
    workbook = Workbook()
    workbook.active.append(headers)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_template_analysis_only_maps_frozen_headers() -> None:
    analysis = analyze_template(_workbook_bytes(["一级类目", "品牌", "毛利", "是否厂直"]))

    assert analysis.sheet_name == "Sheet"
    assert analysis.header_row == 1
    assert analysis.data_start_row == 2
    assert analysis.mapping_json == {
        "category_level1_name": "一级类目",
        "brand": "品牌",
        "factory_direct": "是否厂直",
    }
    assert "profit" not in analysis.mapping_json
    assert "gross_margin" not in analysis.mapping_json


def test_mapping_contract_rejects_unknown_database_fields() -> None:
    with pytest.raises(ValidationError):
        RecommendationTemplateMappingUpdateRequest(
            sheet_name="Sheet",
            header_row=1,
            data_start_row=2,
            mapping_json={"created_by": "创建人"},
        )


def test_mapping_contract_accepts_product_master_fields() -> None:
    payload = RecommendationTemplateMappingUpdateRequest(
        sheet_name="Sheet",
        header_row=1,
        data_start_row=2,
        mapping_json={"company_name": "所属公司", "after_sales_policy": "售后政策"},
    )

    assert payload.mapping_json["company_name"] == "所属公司"


def test_template_structure_returns_actual_headers_and_marks_duplicates() -> None:
    content = _workbook_bytes(["商品名称", "品牌", "品牌", "", "自定义列"])

    structure = inspect_template_structure(content, sheet_name="Sheet", header_row=1)

    assert structure.sheet_names == ["Sheet"]
    assert [
        (column.column_index, column.header, column.duplicate) for column in structure.columns
    ] == [
        (1, "商品名称", False),
        (2, "品牌", True),
        (3, "品牌", True),
        (5, "自定义列", False),
    ]


def test_mapping_contract_requires_existing_sheet_rows_and_headers() -> None:
    content = _workbook_bytes(["品牌", "名称"])
    with pytest.raises(AppError, match="工作表不存在"):
        validate_mapping_contract(
            content, sheet_name="不存在", header_row=1, data_start_row=2, mapping_json={}
        )
    with pytest.raises(AppError, match="数据起始行"):
        validate_mapping_contract(
            content, sheet_name="Sheet", header_row=1, data_start_row=1, mapping_json={}
        )
    with pytest.raises(AppError, match="源表头不存在"):
        validate_mapping_contract(
            content,
            sheet_name="Sheet",
            header_row=1,
            data_start_row=2,
            mapping_json={"brand": "未知"},
        )
    validate_mapping_contract(
        content, sheet_name="Sheet", header_row=1, data_start_row=2, mapping_json={"brand": "品牌"}
    )
