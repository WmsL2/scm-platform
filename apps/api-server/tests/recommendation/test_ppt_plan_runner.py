from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
)
from app.modules.recommendation.ppt_schemas import PptPlanProposal, PptPlanProposalList


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
async def test_type5_plan_runner_only_exposes_frozen_candidate_ids() -> None:
    candidates = [_candidate("120"), _candidate("180"), _candidate("250")]
    output = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=1,
                name="方案一",
                candidate_ids=[candidates[0].id, candidates[1].id],
            )
        ]
    )
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=2,
        plan_count_per_band=1,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    result = await PptPlanAgentRunner(FakeProvider(output)).run(config, candidates)

    assert result == output


@pytest.mark.asyncio
async def test_type5_plan_runner_does_not_apply_a_total_candidate_pool_limit() -> None:
    candidates = [_candidate("120") for _ in range(1001)]
    provider = FakeProvider(PptPlanProposalList())
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=200,
        plan_count_per_band=1,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    result = await PptPlanAgentRunner(provider).run(config, candidates)

    assert result.plans == []
    assert len(provider.calls) == 1
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert len(sent["price_band"]["candidates"]) == 1001
