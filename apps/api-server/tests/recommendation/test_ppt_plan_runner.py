from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.ppt_schemas import (
    PptFrozenRecommendationConfig,
    PptPlanProposal,
    PptPlanProposalList,
)


class FakeProvider:
    provider = "fake"
    model = "fake-model"
    prompt_version = "ppt-plan-test"

    def __init__(self, output: PptPlanProposalList) -> None:
        self.output = output
        self.calls: list[dict[str, Any]] = []

    async def structured_completion(self, **kwargs: Any) -> PptPlanProposalList:
        assert kwargs["response_model"] is PptPlanProposalList
        self.calls.append(kwargs)
        return self.output


def _candidate(price: str) -> RecommendationCandidate:
    return RecommendationCandidate(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        rank=1,
        product_snapshot={"product_name": "测试商品", "brand": "品牌"},
        supplier_snapshot={},
        price_snapshot={"agreement_price": price},
    )


@pytest.mark.asyncio
async def test_type5_plan_runner_exposes_only_short_window_keys() -> None:
    candidates = [_candidate("120"), _candidate("180"), _candidate("250")]
    output = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=1,
                name="方案一",
                candidate_keys=["c1", "c2"],
            )
        ]
    )
    config = PptFrozenRecommendationConfig(
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=2,
        plan_count_per_band=1,
        fulfillment_deadline=None,
    )

    provider = FakeProvider(output)
    result = await PptPlanAgentRunner(provider).run(config, candidates)

    assert result == output
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert sent["candidates"][0]["id"] == "c1"
    assert str(candidates[0].id) not in provider.calls[0]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_bounds_ai_window_without_truncating_complete_pool() -> None:
    candidates = [_candidate("120") for _ in range(1001)]
    provider = FakeProvider(PptPlanProposalList())
    config = PptFrozenRecommendationConfig(
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=200,
        plan_count_per_band=1,
        fulfillment_deadline=None,
    )

    result = await PptPlanAgentRunner(provider).run(config, candidates)

    assert result.plans == []
    assert len(provider.calls) == 1
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert len(sent["candidates"]) < 1001
    assert len(candidates) == 1001
