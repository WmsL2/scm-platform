from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook

from app.modules.matching.application.type1_agent import (
    Type1Agent,
    Type1BatchMatchResult,
    Type1CandidateContext,
    Type1RequirementContext,
    Type1TemplateMappingSuggestion,
)


class StubType1Provider:
    provider = "stub"
    model = "stub-type1"
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
    sheet.title = "需求明细"
    sheet.append(["三级类目", "商品名称", "规格参数", "主要技术要求", "限价", "特殊备注", "报价"])
    sheet.append(["办公耗材", "黑色粉盒", "1500页", "适用指定机型", 100, "单支装", None])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@pytest.mark.asyncio
async def test_type1_template_agent_uses_fixed_reference_semantics_and_notes() -> None:
    provider = StubType1Provider(
        [
            Type1TemplateMappingSuggestion.model_validate(
                {
                    "sheet_name": "需求明细",
                    "header_row": 1,
                    "data_start_row": 2,
                    "input_mapping": {
                        "category_text": "三级类目",
                        "product_name": "商品名称",
                        "specification": "规格参数",
                        "technical_requirements": "主要技术要求",
                        "max_price": "限价",
                        "row_note": "特殊备注",
                    },
                    "output_mapping": {"selected_unit_price": "报价"},
                }
            )
        ]
    )

    result = await Type1Agent(provider).suggest_template_mapping(
        _workbook_bytes(), project_remark="项目备注也要参考"
    )

    assert result.input_mapping.technical_requirements == "主要技术要求"
    prompt = provider.calls[0]["system_prompt"]
    assert "三级类目、商品名称、规格型号或规格参数、主要技术要求、限价" in prompt
    assert "行备注或特殊备注" in prompt


@pytest.mark.asyncio
async def test_type1_match_agent_treats_missing_product_fields_as_unknown() -> None:
    context = Type1RequirementContext(
        requirement_key="R0123456789ab",
        source_row={"商品名称": "黑色粉盒", "特殊备注": "单支装"},
        normalized_fields={"product_name": "黑色粉盒", "specification": "1500页"},
        important_fields={"product_name": "黑色粉盒", "row_note": "单支装"},
        candidates=[
            Type1CandidateContext(
                candidate_key="P01",
                product_name="黑色粉盒",
                specification=None,
                packaging=None,
            )
        ],
    )
    provider = StubType1Provider(
        [
            Type1BatchMatchResult.model_validate(
                {
                    "items": [
                        {
                            "requirement_key": context.requirement_key,
                            "candidate_keys": ["P01"],
                        }
                    ]
                }
            )
        ]
    )

    await Type1Agent(provider).match_batch([context], project_remark="备注优先参考")

    prompt = provider.calls[0]["system_prompt"]
    assert "只表示未知，不得因此排除" in prompt
    assert "明确冲突时才排除" in prompt
    assert "数量只用于报价数量" in prompt
    payload = json.loads(provider.calls[0]["user_prompt"])
    assert payload["project_remark"] == "备注优先参考"


@pytest.mark.asyncio
async def test_type1_match_agent_retries_an_incomplete_batch_contract() -> None:
    context = Type1RequirementContext(
        requirement_key="R0123456789ab",
        source_row={"商品名称": "电话机"},
        normalized_fields={"product_name": "电话机"},
        important_fields={"product_name": "电话机"},
        candidates=[Type1CandidateContext(candidate_key="P01", product_name="电话机")],
    )
    provider = StubType1Provider(
        [
            Type1BatchMatchResult(items=[]),
            Type1BatchMatchResult.model_validate(
                {
                    "items": [
                        {
                            "requirement_key": context.requirement_key,
                            "candidate_keys": ["P01"],
                        }
                    ]
                }
            ),
        ]
    )

    result = await Type1Agent(provider).match_batch([context], project_remark=None)

    assert result.items[0].candidate_keys == ["P01"]
    assert len(provider.calls) == 2
    assert "违反批次业务合同" in provider.calls[1]["user_prompt"]
