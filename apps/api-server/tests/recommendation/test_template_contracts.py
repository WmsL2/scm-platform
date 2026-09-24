from io import BytesIO

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.common.contracts import AppError
from app.modules.recommendation.template.analyzer import analyze_template, validate_mapping_contract
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
    assert analysis.mapping_json == {"category_level1_name": "一级类目", "brand": "品牌"}
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


def test_mapping_contract_rejects_empty_mapping_before_confirmation() -> None:
    with pytest.raises(ValidationError):
        RecommendationTemplateMappingUpdateRequest(
            sheet_name="Sheet", header_row=1, data_start_row=2, mapping_json={}
        )


def test_mapping_contract_accepts_manual_confirmation_export_fields() -> None:
    payload = RecommendationTemplateMappingUpdateRequest(
        sheet_name="Sheet",
        header_row=1,
        data_start_row=2,
        mapping_json={
            "campaign_price": "活动价",
            "delivery_status": "发货状态",
            "inventory_status": "库存状态",
            "fulfillment_cycle": "履约说明",
            "evidence": "依据与备注",
        },
    )
    assert payload.mapping_json["campaign_price"] == "活动价"


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
