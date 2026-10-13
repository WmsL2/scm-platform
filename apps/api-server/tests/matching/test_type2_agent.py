from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.modules.matching.application.type2_agent import (
    Type2Agent,
    Type2AgentContractError,
    Type2BatchMatchResult,
    Type2CandidateContext,
    Type2RequirementContext,
    Type2TemplateMappingSuggestion,
)


class StubType2Provider:
    provider = "stub"
    model = "stub-type2"
    prompt_version = "test"

    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def structured_completion(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "报价明细"
    sheet.append(["客户", "品牌", "型号", "适用机型", "行备注", "商品报价", "备注"])
    sheet.append(["北京烟草", "联想", "LT1821", "CS1821W", "必须原装", None, None])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_type2_mapping_requires_an_identity_source_column() -> None:
    with pytest.raises(ValidationError, match="可提取品牌型号"):
        Type2TemplateMappingSuggestion.model_validate(
            {
                "sheet_name": "报价明细",
                "header_row": 1,
                "data_start_row": 2,
                "input_mapping": {"brand": "品牌"},
                "output_mapping": {"selected_unit_price": "商品报价"},
            }
        )


def test_type2_mapping_accepts_brand_and_model_embedded_in_parameter_text() -> None:
    mapping = Type2TemplateMappingSuggestion.model_validate(
        {
            "sheet_name": "报价明细",
            "header_row": 1,
            "data_start_row": 2,
            "input_mapping": {"specification": "规格型号/参数"},
            "output_mapping": {"selected_unit_price": "商品报价"},
        }
    )

    assert mapping.input_mapping.specification == "规格型号/参数"


def test_type2_template_mapping_allows_human_fallback_for_output_column() -> None:
    mapping = Type2TemplateMappingSuggestion.model_validate(
        {
            "sheet_name": "报价明细",
            "header_row": 1,
            "data_start_row": 2,
            "input_mapping": {"brand": "品牌", "model": "型号"},
            "output_mapping": {"selected_unit_price": None},
        }
    )

    assert mapping.output_mapping.selected_unit_price is None


@pytest.mark.asyncio
async def test_type2_template_agent_maps_real_columns_from_an_unknown_workbook() -> None:
    provider = StubType2Provider(
        [
            Type2TemplateMappingSuggestion.model_validate(
                {
                    "sheet_name": "报价明细",
                    "header_row": 1,
                    "data_start_row": 2,
                    "input_mapping": {
                        "brand": "品牌",
                        "model": "型号",
                        "specification": "适用机型",
                    },
                    "output_mapping": {
                        "selected_unit_price": "商品报价",
                        "note": "备注",
                    },
                }
            )
        ]
    )

    result = await Type2Agent(provider).suggest_template_mapping(
        _workbook_bytes(), project_remark="原品优先，确实没有时才允许同类替代"
    )

    assert result.output_mapping.selected_unit_price == "商品报价"
    call = provider.calls[0]
    assert "类型2指定商品报价" in call["system_prompt"]
    payload = json.loads(call["user_prompt"])
    assert payload["project_remark"] == "原品优先，确实没有时才允许同类替代"
    assert payload["workbook"]["sheets"][0]["sample_rows"][0]["values"][4] == "行备注"


@pytest.mark.asyncio
async def test_type2_match_agent_receives_full_row_and_project_remark() -> None:
    context = Type2RequirementContext(
        requirement_key="R0123456789ab",
        source_row={
            "品牌": "联想",
            "型号": "LT1821",
            "颜色": "黑",
            "适用机型": "CS1821W",
            "备注": "必须原装单支装",
        },
        normalized_fields={"brand": "联想", "model": "LT1821"},
        candidates=[
            Type2CandidateContext(
                candidate_key="P01",
                product_name="联想 LT1821 黑色原装粉盒",
                brand="联想Lenovo",
                model="LT-1821",
                specification="黑色，适用 CS1821W",
                packaging="单支装",
            )
        ],
    )
    provider = StubType2Provider(
        [
            Type2BatchMatchResult.model_validate(
                {
                    "items": [
                        {
                            "requirement_key": context.requirement_key,
                            "exact_candidate_keys": ["P01"],
                            "substitute_candidates": [],
                        }
                    ]
                }
            )
        ]
    )

    await Type2Agent(provider).match_batch(
        [context], project_remark="报价需满足平台 88 折并长期履约"
    )

    call = provider.calls[0]
    assert "类型2专属提示词" in call["system_prompt"]
    assert "项目备注可作为全局约束" in call["system_prompt"]
    assert "只表示未知，不得仅因" in call["system_prompt"]
    assert "预计数量只用于采购数量" in call["system_prompt"]
    assert "明确冲突时仍不得判为EXACT" in call["system_prompt"]
    payload = json.loads(call["user_prompt"])
    assert payload["project_remark"] == "报价需满足平台 88 折并长期履约"
    assert payload["requirements"][0]["source_row"]["备注"] == "必须原装单支装"


@pytest.mark.asyncio
async def test_type2_agent_rejects_substitute_without_mandatory_note() -> None:
    context = Type2RequirementContext(
        requirement_key="R0123456789ab",
        source_row={"型号": "LT1821"},
        normalized_fields={"model": "LT1821"},
        allow_substitution=True,
        candidates=[Type2CandidateContext(candidate_key="P01", model="LT1821C")],
    )
    provider = StubType2Provider(
        [
            Type2BatchMatchResult.model_validate(
                {
                    "items": [
                        {
                            "requirement_key": context.requirement_key,
                            "exact_candidate_keys": [],
                            "substitute_candidates": [
                                {
                                    "candidate_key": "P01",
                                    "differences": ["型号不同"],
                                    "note": "推荐相近型号",
                                }
                            ],
                        }
                    ]
                }
            )
        ]
    )

    with pytest.raises(Type2AgentContractError, match="强制替代备注"):
        await Type2Agent(provider).match_batch([context], project_remark=None)
