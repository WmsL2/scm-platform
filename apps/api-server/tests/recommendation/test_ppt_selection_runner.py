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

    async def structured_completion(self, **kwargs: Any) -> Any:
        self.response_models.append(kwargs["response_model"].__name__)
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
