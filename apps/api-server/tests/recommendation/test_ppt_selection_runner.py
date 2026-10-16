from __future__ import annotations

from typing import Any

import pytest

from app.modules.recommendation.application.agent_schemas import (
    CategoryCatalogMatch,
    RequirementAnalysis,
)
from app.modules.recommendation.application.ppt_selection_runner import (
    PptSelectionAgentRunner,
)
from app.modules.recommendation.schemas import CategoryCatalogItem, CategoryCatalogSnapshot


class FakeProvider:
    provider = "fake"
    model = "fake-model"
    prompt_version = "ppt-test"

    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.response_models: list[str] = []
        self.system_prompts: list[str] = []

    async def structured_completion(self, **kwargs: Any) -> Any:
        self.response_models.append(kwargs["response_model"].__name__)
        self.system_prompts.append(kwargs["system_prompt"])
        return self.outputs.pop(0)


class FakePptTools:
    def __init__(self) -> None:
        self.prepared: RequirementAnalysis | None = None

    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot:
        self.prepared = analysis
        return CategoryCatalogSnapshot(
            generated_at="2026-09-30T00:00:00Z",
            items=[
                CategoryCatalogItem(
                    category_key="c1",
                    level="LEVEL3",
                    level1_name="日用品",
                    level2_name="床上用品",
                    level3_name="毛毯",
                    candidate_count=70,
                )
            ],
        )

    async def record_catalog_category_matches(self, category_keys: list[str]) -> None:
        self.category_keys = category_keys


@pytest.mark.asyncio
async def test_type5_runner_selects_categories_but_does_not_rank_products() -> None:
    analysis = RequirementAnalysis(
        summary="慰问品", keywords=["慰问品"], explicit_category_keywords=["毛毯"]
    )
    provider = FakeProvider(
        [
            analysis,
            CategoryCatalogMatch(category_keys=["c1"]),
        ]
    )
    tools = FakePptTools()

    result = await PptSelectionAgentRunner(provider, tools).run(
        "上海外高桥船厂慰问品项目推品，需要日用品，履约至二零二七年十二月。"
    )

    assert tools.prepared is analysis
    assert tools.category_keys == ["c1"]
    assert result.candidates == []
    assert provider.response_models == ["RequirementAnalysis", "CategoryCatalogMatch"]


@pytest.mark.asyncio
async def test_type5_runner_does_not_treat_welfare_fee_tiers_as_single_product_prices() -> None:
    analysis = RequirementAnalysis(
        summary="员工慰问品",
        keywords=["慰问品"],
        budget_min=100,
        budget_max=500,
        agreement_price_min=100,
        agreement_price_max=500,
    )
    provider = FakeProvider([analysis])
    tools = FakePptTools()

    await PptSelectionAgentRunner(provider, tools).run(
        "会员慰问品费用档位为 100 元、200 元、300 元和 500 元，需要食品方案。"
    )

    prompt = provider.system_prompts[0]
    assert "页面价格档唯一控制" in prompt
    assert "费用档位、慰问标准、方案预算" in prompt
    assert "agreement_price_min/max 或 budget_min/max" in prompt
