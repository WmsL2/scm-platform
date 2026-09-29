from __future__ import annotations

from typing import Any

import pytest

from app.integrations.deepseek.client import DeepSeekStructuredOutputError
from app.modules.recommendation.application.agent_runner import (
    AgentRunner,
    RecommendationAgentCancelled,
)
from app.modules.recommendation.application.agent_schemas import (
    CategoryCatalogMatch,
    RequirementAnalysis,
)
from app.modules.recommendation.schemas import CategoryCatalogSnapshot


class FakeProvider:
    provider = "fake"
    model = "fake-model"
    prompt_version = "free-v4"

    def __init__(self, outputs: list[RequirementAnalysis | Exception]) -> None:
        self.outputs = outputs
        self.system_prompts: list[str] = []

    async def structured_completion(self, **kwargs: Any) -> RequirementAnalysis:
        self.system_prompts.append(kwargs["system_prompt"])
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class FakeTools:
    def __init__(self) -> None:
        self.prepared: RequirementAnalysis | None = None
        self.catalog_matches: list[str] | None = None

    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot:
        self.prepared = analysis
        return CategoryCatalogSnapshot(
            generated_at="2026-09-29T00:00:00Z",
            items=[
                {
                    "category_key": "c1",
                    "level1_name": "家居日用",
                    "level2_name": "水具酒具",
                    "level3_name": "保温杯",
                    "candidate_count": 4,
                }
            ],
        )

    async def record_catalog_category_matches(self, category_keys: list[str]) -> None:
        self.catalog_matches = category_keys


@pytest.mark.asyncio
async def test_agent_parses_numeric_and_explicit_brand_category_constraints() -> None:
    analysis = RequirementAnalysis(
        summary="中秋出行推品",
        keywords=["中秋"],
        explicit_category_keywords=["家电", "厨具", "日用"],
        category_intents=["家电", "生活电器", "厨具", "厨房用品", "日用"],
        required_brands=["指定品牌"],
        scenarios=["中秋十一出行"],
        quantity=1,
        discount_rate_max="0.9",
    )
    provider = FakeProvider([analysis, CategoryCatalogMatch(category_keys=["c1"])])
    tools = FakeTools()

    result = await AgentRunner(provider, tools).run(
        "中秋十一出行自由推品，VIP价可满足九折，库存稳定。"
    )

    assert result.candidates == []
    assert result.category_choices == []
    assert result.tool_call_count == 0
    assert tools.prepared is analysis
    assert tools.catalog_matches == ["c1"]
    assert "required_brands" in provider.system_prompts[0]
    assert "category_intents 必须返回空数组" in provider.system_prompts[0]
    assert "需要水杯、保温杯、随行杯" in provider.system_prompts[0]
    assert "类目 + 数量" in provider.system_prompts[0]
    assert "discount_rate_max=0.9" in provider.system_prompts[0]
    assert "category_catalog.items" in provider.system_prompts[1]


@pytest.mark.asyncio
async def test_agent_does_not_prepare_a_run_that_needs_input() -> None:
    analysis = RequirementAnalysis(
        summary="存在冲突",
        keywords=["冲突"],
        needs_input=True,
        blocking_reasons=["CONTRADICTORY_CONSTRAINTS"],
        questions=["请确认价格范围"],
    )
    tools = FakeTools()

    result = await AgentRunner(FakeProvider([analysis]), tools).run(
        "一段足够长的自由推品需求，用于验证冲突处理流程。"
    )

    assert result.analysis.needs_input is True
    assert tools.prepared is None


@pytest.mark.asyncio
async def test_agent_retries_safe_structured_analysis_failure_and_honours_cancellation() -> None:
    error = DeepSeekStructuredOutputError(
        response_model_name="RequirementAnalysis",
        safe_validation_summary="discount_rate_max: invalid",
        error_kind="SCHEMA_VALIDATION",
    )
    analysis = RequirementAnalysis(summary="测试", keywords=["测试"])
    provider = FakeProvider([error, analysis])
    tools = FakeTools()

    result = await AgentRunner(provider, tools).run(
        "一段足够长的自由推品需求，用于验证结构化结果重试。"
    )

    assert result.analysis == analysis
    assert len(provider.system_prompts) == 2
    with pytest.raises(RecommendationAgentCancelled):
        await AgentRunner(FakeProvider([analysis]), FakeTools()).run(
            "一段足够长的自由推品需求，用于验证任务取消处理。",
            is_cancelled=_cancelled,
        )


async def _cancelled() -> bool:
    return True
