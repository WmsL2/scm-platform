from __future__ import annotations

from typing import Any

import pytest

from app.modules.recommendation.application.agent_schemas import (
    CategoryChoice,
    CategoryChoiceList,
    CategoryOption,
    RequirementAnalysis,
)
from app.modules.recommendation.application.ppt_selection_runner import (
    PptSelectionAgentRunner,
)


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

    async def prepare(self, analysis: RequirementAnalysis) -> None:
        self.prepared = analysis

    async def list_categories(
        self, keywords: list[str], *, limit: int
    ) -> list[CategoryOption]:
        del keywords, limit
        return [
            CategoryOption(
                key="category-1",
                level1="日用品",
                level2="床上用品",
                level3="毛毯",
                product_count=70,
            )
        ]


@pytest.mark.asyncio
async def test_type5_runner_selects_categories_but_does_not_rank_products() -> None:
    analysis = RequirementAnalysis(summary="慰问品", keywords=["慰问品"])
    provider = FakeProvider(
        [
            analysis,
            CategoryChoiceList(
                choices=[
                    CategoryChoice(
                        category_key="category-1",
                        search_keywords=["毛毯"],
                        reason="符合需求",
                    )
                ]
            ),
        ]
    )
    tools = FakePptTools()

    result = await PptSelectionAgentRunner(provider, tools).run(
        "上海外高桥船厂慰问品项目推品，需要日用品，履约至二零二七年十二月。"
    )

    assert tools.prepared is analysis
    assert [choice.category_key for choice in result.category_choices] == ["category-1"]
    assert result.candidates == []
    assert provider.response_models == ["RequirementAnalysis", "CategoryChoiceList"]
