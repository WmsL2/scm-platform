from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.integrations.deepseek.client import DeepSeekStructuredOutputError
from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
)
from app.modules.recommendation.ppt_schemas import PptPlanReferenceProposal


class FakeProvider:
    provider = "fake"
    model = "fake-model"
    prompt_version = "ppt-plan-test"

    def __init__(self, outputs: list[PptPlanReferenceProposal | Exception]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, Any]] = []

    async def structured_completion(self, **kwargs: Any) -> PptPlanReferenceProposal:
        assert kwargs["response_model"] is PptPlanReferenceProposal
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
            "sku": f"SKU-{rank}",
            "product_name": f"测试商品 {rank}",
            "brand": "品牌",
        },
        supplier_snapshot={"supplier_code": "SUP000001"},
        price_snapshot={"agreement_price": price},
    )


def _config(*, items: int, plans: int) -> PptRecommendationConfig:
    return PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=items,
        plan_count_per_band=plans,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_type5_plan_runner_maps_short_refs_to_frozen_candidate_ids() -> None:
    candidates = [
        _candidate("120", rank=1),
        _candidate("180", rank=2),
        _candidate("250", rank=3),
    ]
    provider = FakeProvider(
        [PptPlanReferenceProposal(name="方案一", candidate_refs=["P0001", "P0002"])]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=2, plans=1), candidates)

    assert result.plans[0].candidate_ids == [candidates[0].id, candidates[1].id]
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert sent["price_band"]["candidate_columns"][0] == "candidate_ref"
    assert sent["price_band"]["candidates"][0][0] == "P0001"
    assert "candidate_id" not in provider.calls[0]["user_prompt"]
    assert str(candidates[0].id) not in provider.calls[0]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_calls_provider_once_per_plan() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 5)]
    provider = FakeProvider(
        [
            PptPlanReferenceProposal(name="方案一", candidate_refs=["P0001", "P0002"]),
            PptPlanReferenceProposal(name="方案二", candidate_refs=["P0003", "P0004"]),
        ]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=2, plans=2), candidates)

    assert len(provider.calls) == 2
    assert [plan.plan_no for plan in result.plans] == [1, 2]
    assert result.plans[0].candidate_ids != result.plans[1].candidate_ids


@pytest.mark.asyncio
async def test_type5_plan_runner_retries_structured_output_per_plan() -> None:
    candidates = [_candidate("120", rank=1), _candidate("130", rank=2)]
    provider = FakeProvider(
        [
            DeepSeekStructuredOutputError(
                response_model_name="PptPlanReferenceProposal",
                safe_validation_summary="candidate_refs: json_invalid",
                error_kind="INVALID_JSON",
            ),
            PptPlanReferenceProposal(name="重试成功", candidate_refs=["P0001", "P0002"]),
        ]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=2, plans=1), candidates)

    assert len(provider.calls) == 2
    assert result.plans[0].name == "重试成功"
    assert "脱敏错误" in provider.calls[1]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_retries_unknown_refs_per_plan() -> None:
    candidates = [_candidate("120", rank=1), _candidate("130", rank=2)]
    provider = FakeProvider(
        [
            PptPlanReferenceProposal(name="错误方案", candidate_refs=["P0001", "P9999"]),
            PptPlanReferenceProposal(name="修正方案", candidate_refs=["P0001", "P0002"]),
        ]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=2, plans=1), candidates)

    assert len(provider.calls) == 2
    assert result.plans[0].name == "修正方案"
    assert "后端校验" in provider.calls[1]["user_prompt"]


@pytest.mark.asyncio
async def test_type5_plan_runner_keeps_valid_plan_when_provider_returns_fewer_items() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 5)]
    provider = FakeProvider(
        [PptPlanReferenceProposal(name="不足目标数量", candidate_refs=["P0001", "P0002"])]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=3, plans=1), candidates)

    assert len(provider.calls) == 1
    assert result.plans[0].candidate_ids == [candidates[0].id, candidates[1].id]


@pytest.mark.asyncio
async def test_type5_plan_runner_caps_provider_items_at_configured_target() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 5)]
    provider = FakeProvider(
        [
            PptPlanReferenceProposal(
                name="超过目标数量",
                candidate_refs=["P0001", "P0002", "P0003", "P0004"],
            )
        ]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=3, plans=1), candidates)

    assert result.plans[0].candidate_ids == [
        candidates[0].id,
        candidates[1].id,
        candidates[2].id,
    ]


@pytest.mark.asyncio
async def test_type5_plan_runner_keeps_large_pool_but_returns_compact_refs() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 1002)]
    refs = [f"P{index:04d}" for index in range(1, 201)]
    provider = FakeProvider([PptPlanReferenceProposal(name="大方案", candidate_refs=refs)])

    result = await PptPlanAgentRunner(provider).run(_config(items=200, plans=1), candidates)

    assert len(result.plans[0].candidate_ids) == 200
    assert len(provider.calls) == 1
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert len(sent["price_band"]["candidates"]) == 1001
    assert sent["price_band"]["candidates"][-1][0] == "P1001"
