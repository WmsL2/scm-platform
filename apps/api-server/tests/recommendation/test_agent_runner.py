from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from app.modules.recommendation.application.agent_runner import (
    AgentRunner,
    RecommendationAgentCancelled,
    RecommendationAgentContractError,
)
from app.modules.recommendation.application.agent_schemas import (
    CandidateRanking,
    CategoryChoice,
    CategoryChoiceList,
    CategoryOption,
    ProductCandidate,
    ProductSearchRequest,
    RankedCandidate,
    RequirementAnalysis,
    RequirementBlockingReason,
)


class FakeProvider:
    provider = "fake-deepseek"
    model = "fake-model"
    prompt_version = "test-v1"

    def __init__(self, responses: list[BaseModel | Exception]) -> None:
        self.responses = responses
        self.calls = 0
        self.system_prompts: list[str] = []

    async def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> Any:
        del user_prompt
        self.system_prompts.append(system_prompt)
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, response_model)
        return response


class FakeTools:
    def __init__(self, product: ProductCandidate) -> None:
        self.product = product
        self.searches: list[ProductSearchRequest] = []
        self.prepared: RequirementAnalysis | None = None

    async def prepare(self, analysis: RequirementAnalysis) -> None:
        self.prepared = analysis

    async def list_categories(self, keywords: list[str], *, limit: int) -> list[CategoryOption]:
        assert keywords == ["会议", "显示"]
        assert limit == 100
        return [
            CategoryOption(
                key="办公设备/会议设备/会议平板",
                level1="办公设备",
                level2="会议设备",
                level3="会议平板",
                product_count=12,
            )
        ]

    async def search_products(self, request: ProductSearchRequest) -> list[ProductCandidate]:
        self.searches.append(request)
        return [self.product]


def analysis() -> RequirementAnalysis:
    return RequirementAnalysis(
        summary="企业会议室需要可靠的显示与协作设备",
        keywords=["会议", "显示"],
        scenarios=["企业会议室"],
        budget_max=Decimal("10000"),
    )


@pytest.mark.asyncio
async def test_agent_uses_real_category_keys_and_only_ranks_returned_products() -> None:
    product_id = uuid4()
    product = ProductCandidate(
        product_id=product_id,
        product_name="65英寸会议平板",
        brand="示例品牌",
        category_path="办公设备/会议设备/会议平板",
        agreement_price=Decimal("8999"),
        highlights=["无线投屏"],
    )
    provider = FakeProvider(
        [
            analysis(),
            CategoryChoiceList(
                choices=[
                    CategoryChoice(
                        category_key="办公设备/会议设备/会议平板",
                        reason="适合会议协作",
                        search_keywords=["会议平板"],
                    )
                ]
            ),
            CandidateRanking(
                candidates=[
                    RankedCandidate(product_id=product_id, score=Decimal("91"), reason="符合预算")
                ]
            ),
        ]
    )
    tools = FakeTools(product)
    progress: list[tuple[str, int]] = []

    async def report(status: str, percent: int, _: str) -> None:
        progress.append((status, percent))

    result = await AgentRunner(provider, tools).run(
        "我们需要一套适合企业会议室使用的显示和无线协作设备，请优先考虑可靠性",
        report_progress=report,
    )

    assert result.candidates[0].product_id == product_id
    assert result.tool_call_count == 2
    assert tools.prepared == analysis()
    assert tools.searches[0].agreement_price_max == Decimal("10000")
    assert progress[-1] == ("CANDIDATES_READY", 100)
    assert "不指定类目、品牌、单价、预算和数量" in provider.system_prompts[0]


@pytest.mark.asyncio
async def test_agent_retries_provider_once() -> None:
    need_input = analysis().model_copy(
        update={
            "needs_input": True,
            "blocking_reasons": [RequirementBlockingReason.COMPLIANCE_DECISION_REQUIRED],
            "questions": ["请确认是否涉及必须人工审批的合规限制"],
        }
    )
    provider = FakeProvider([RuntimeError("temporary"), need_input])
    result = await AgentRunner(provider, FakeTools(_unused_product())).run(
        "我们需要为企业活动准备一批员工福利商品，请根据使用场景给出方向"
    )
    assert result.analysis.needs_input is True
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_agent_rejects_invented_category_and_honours_cancellation() -> None:
    provider = FakeProvider(
        [
            analysis(),
            CategoryChoiceList(
                choices=[
                    CategoryChoice(
                        category_key="不存在/不存在/不存在",
                        reason="虚构类目",
                        search_keywords=["商品"],
                    )
                ]
            ),
        ]
    )
    with pytest.raises(RecommendationAgentContractError, match="不存在的类目"):
        await AgentRunner(provider, FakeTools(_unused_product())).run(
            "我们需要一套适合企业会议室使用的显示和无线协作设备，请优先考虑可靠性"
        )

    async def cancelled() -> bool:
        return True

    with pytest.raises(RecommendationAgentCancelled):
        await AgentRunner(FakeProvider([]), FakeTools(_unused_product())).run(
            "我们需要一套适合企业会议室使用的显示和无线协作设备，请优先考虑可靠性",
            is_cancelled=cancelled,
        )


def _unused_product() -> ProductCandidate:
    return ProductCandidate(
        product_id=UUID("00000000-0000-0000-0000-000000000001"),
        product_name="占位商品",
        category_path="一级/二级/三级",
    )
