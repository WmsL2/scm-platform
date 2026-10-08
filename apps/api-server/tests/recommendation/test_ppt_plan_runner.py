from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.integrations.deepseek.client import DeepSeekStructuredOutputError
from app.modules.recommendation.application.agent_runner import RecommendationAgentContractError
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

    def __init__(self, outputs: list[PptPlanProposalList | Exception]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, Any]] = []

    async def structured_completion(self, **kwargs: Any) -> PptPlanProposalList:
        assert kwargs["response_model"] is PptPlanProposalList
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def _candidate(price: str, *, rank: int = 1) -> RecommendationCandidate:
    return RecommendationCandidate(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        rank=rank,
        product_snapshot={
            "product_name": f"测试商品 {rank}",
            "brand": "品牌",
            "category_level3_name": "测试三级类目",
        },
        supplier_snapshot={},
        price_snapshot={"agreement_price": price},
    )


def _config(*, items: int, plans: int) -> PptFrozenRecommendationConfig:
    return PptFrozenRecommendationConfig(
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=items,
        plan_count_per_band=plans,
        fulfillment_deadline=None,
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

    provider = FakeProvider([output])
    result = await PptPlanAgentRunner(provider).run(_config(items=2, plans=1), candidates)

    assert result == output
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert sent["candidates"][0]["id"] == "c1"
    assert str(candidates[0].id) not in provider.calls[0]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_bounds_ai_window_without_truncating_complete_pool() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 1002)]
    provider = FakeProvider([PptPlanProposalList()])

    result = await PptPlanAgentRunner(provider).run(_config(items=200, plans=1), candidates)

    assert result.plans == []
    assert len(provider.calls) == 1
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert len(sent["candidates"]) < len(candidates)
    assert len(candidates) == 1001


@pytest.mark.asyncio
async def test_type5_plan_runner_retries_structured_output_without_expanding_input() -> None:
    output = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=1,
                name="重试成功",
                candidate_keys=["c1"],
            )
        ]
    )
    provider = FakeProvider(
        [
            DeepSeekStructuredOutputError(
                response_model_name="PptPlanProposalList",
                safe_validation_summary="plans: json_invalid",
                error_kind="INVALID_JSON",
            ),
            output,
        ]
    )

    result = await PptPlanAgentRunner(provider).run(
        _config(items=2, plans=1), [_candidate("120"), _candidate("130")]
    )

    assert result == output
    assert len(provider.calls) == 2
    assert "脱敏错误" in provider.calls[1]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_rejects_key_outside_ai_window() -> None:
    provider = FakeProvider(
        [
            PptPlanProposalList(
                plans=[
                    PptPlanProposal(
                        price_band_index=1,
                        plan_no=1,
                        name="越界方案",
                        candidate_keys=["c999"],
                    )
                ]
            )
        ]
    )

    with pytest.raises(RecommendationAgentContractError, match="清单外商品"):
        await PptPlanAgentRunner(provider).run(
            _config(items=2, plans=1), [_candidate("120"), _candidate("130")]
        )
