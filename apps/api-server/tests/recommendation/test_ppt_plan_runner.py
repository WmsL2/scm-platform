from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest

from app.core.config import get_settings
from app.integrations.deepseek.client import DeepSeekStructuredOutputError
from app.modules.recommendation.application.agent_runner import RecommendationAgentContractError
from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.ppt_schemas import (
    PptCandidateAssessment,
    PptCandidateAssessmentList,
    PptDirectSelectionProposal,
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


class DirectProvider:
    provider = "fake"
    model = "fake-model"
    prompt_version = "ppt-direct-selection-test"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def structured_completion(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        payload = json.loads(kwargs["user_prompt"])
        response_model = kwargs["response_model"]
        if response_model is PptCandidateAssessmentList:
            return PptCandidateAssessmentList(
                assessments=[
                    PptCandidateAssessment(
                        candidate_key=row["id"],
                        scene_score=70 + min(index, 30),
                        value_score=80,
                        overall_score=70 + min(index, 30),
                    )
                    for index, row in enumerate(payload["candidates"])
                ]
            )
        assert response_model is PptDirectSelectionProposal
        return PptDirectSelectionProposal(
            candidate_keys=[
                row["id"] for row in payload["candidates"][: payload["required_item_count"]]
            ]
        )


class ConcurrentDirectProvider(DirectProvider):
    def __init__(self) -> None:
        super().__init__()
        self.active_assessments = 0
        self.max_active_assessments = 0

    async def structured_completion(self, **kwargs: Any) -> object:
        if kwargs["response_model"] is PptCandidateAssessmentList:
            self.active_assessments += 1
            self.max_active_assessments = max(
                self.max_active_assessments, self.active_assessments
            )
            try:
                await asyncio.sleep(0.02)
                return await super().structured_completion(**kwargs)
            finally:
                self.active_assessments -= 1
        return await super().structured_completion(**kwargs)


def _candidate(
    price: str, *, rank: int = 1, category: str = "测试三级类目"
) -> RecommendationCandidate:
    return RecommendationCandidate(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        rank=rank,
        product_snapshot={
            "product_name": f"测试商品 {rank}",
            "brand": "品牌",
            "category_level3_name": category,
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
    provider = FakeProvider(
        [
            PptPlanProposalList(
                plans=[
                    PptPlanProposal(
                        price_band_index=1,
                        plan_no=1,
                        name="受控窗口方案",
                        candidate_keys=["c1"],
                    )
                ]
            )
        ]
    )

    result = await PptPlanAgentRunner(provider).run(_config(items=200, plans=1), candidates)

    assert result.plans[0].candidate_keys == ["c1"]
    assert len(provider.calls) == 1
    sent = json.loads(provider.calls[0]["user_prompt"])
    assert len(sent["candidates"]) < len(candidates)
    assert len(candidates) == 1001


@pytest.mark.asyncio
async def test_type5_plan_runner_retries_incomplete_plan_slots() -> None:
    incomplete = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=1,
                name="不完整方案",
                candidate_keys=["c1"],
            )
        ]
    )
    complete = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=number,
                name=f"方案 {number}",
                candidate_keys=["c1"],
            )
            for number in range(1, 4)
        ]
    )
    provider = FakeProvider([incomplete, complete])

    result = await PptPlanAgentRunner(provider).run(
        _config(items=10, plans=3),
        [_candidate("120", rank=index) for index in range(1, 12)],
    )

    assert result == complete
    assert len(provider.calls) == 2
    assert "完整且唯一" in provider.calls[1]["user_prompt"]


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
    invalid = PptPlanProposalList(
        plans=[
            PptPlanProposal(
                price_band_index=1,
                plan_no=1,
                name="越界方案",
                candidate_keys=["c999"],
            )
        ]
    )
    provider = FakeProvider([invalid, invalid])

    with pytest.raises(RecommendationAgentContractError, match="清单外商品"):
        await PptPlanAgentRunner(provider).run(
            _config(items=2, plans=1), [_candidate("120"), _candidate("130")]
        )


@pytest.mark.asyncio
async def test_type5_direct_runner_scores_every_frozen_candidate_then_selects_exact_count() -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 7)]
    candidates[0].product_snapshot.update(
        {
            "model": "露营款",
            "product_specification": "轻量、防水",
            "selling_points": "适合户外露营使用",
            "sales_volume": 100,
        }
    )
    candidates[0].price_snapshot.update(
        {"jd_price": "150", "discount_rate": "0.80", "positive_rating": "0.95"}
    )
    provider = DirectProvider()

    selected = await PptPlanAgentRunner(provider).select_direct_candidates(
        1,
        PptFrozenRecommendationConfig.model_validate(
            {
                "recommendation_mode": "SINGLE",
                "price_bands": [{"min_price": "100", "max_price": "200", "item_count": 2}],
                "selection_mode": "DIRECT",
            }
        ).price_bands[0],
        candidates,
        item_count=2,
        scene_context="客户原始需求：户外露营活动，需要实用且性价比高的用品",
    )

    assert len(selected) == 2
    assert all(item.overall_score >= 70 for item in selected)
    assessment_call = json.loads(provider.calls[0]["user_prompt"])
    assert assessment_call["stage"] == "scene_value_assessment"
    assert len(assessment_call["candidates"]) == len(candidates)
    assert assessment_call["candidates"][0]["selling_points"] is not None
    final_call = json.loads(provider.calls[1]["user_prompt"])
    assert final_call["stage"] == "final_direct_selection"
    assert final_call["required_item_count"] == 2


@pytest.mark.asyncio
async def test_type5_direct_runner_keeps_multiple_categories_in_final_shortlist() -> None:
    candidates = [
        *[_candidate("120", rank=index, category="炒锅") for index in range(1, 5)],
        *[_candidate("120", rank=index, category="保温杯") for index in range(5, 9)],
        *[_candidate("120", rank=index, category="毛巾") for index in range(9, 13)],
    ]
    provider = DirectProvider()
    band = PptFrozenRecommendationConfig.model_validate(
        {
            "recommendation_mode": "SINGLE",
            "price_bands": [{"min_price": "100", "max_price": "200", "item_count": 3}],
            "selection_mode": "DIRECT",
        }
    ).price_bands[0]

    selected = await PptPlanAgentRunner(provider).select_direct_candidates(
        1,
        band,
        candidates,
        item_count=3,
        scene_context="客户原始需求：日用品奖品，尽量覆盖实用生活用品",
    )

    final_call = next(
        call for call in provider.calls if call["response_model"] is PptDirectSelectionProposal
    )
    finalist_categories = {
        row["category"] for row in json.loads(final_call["user_prompt"])["candidates"]
    }
    selected_categories = {
        item.candidate.product_snapshot["category_level3_name"] for item in selected
    }
    assert finalist_categories == {"炒锅", "保温杯", "毛巾"}
    assert selected_categories == {"炒锅", "保温杯", "毛巾"}
    assert "尽量覆盖多个三级类目" in final_call["system_prompt"]


@pytest.mark.asyncio
async def test_type5_direct_runner_parallelizes_compact_assessments_and_keeps_full_finalists(
) -> None:
    candidates = [_candidate("120", rank=index) for index in range(1, 162)]
    full_specification = "完整规格说明" * 40
    full_selling_points = "完整卖点说明" * 40
    candidates[79].product_snapshot.update(
        {
            "product_specification": full_specification,
            "selling_points": full_selling_points,
        }
    )
    provider = ConcurrentDirectProvider()
    settings = get_settings().model_copy(update={"ppt_ai_assessment_concurrency": 2})
    band = PptFrozenRecommendationConfig.model_validate(
        {
            "recommendation_mode": "SINGLE",
            "price_bands": [{"min_price": "100", "max_price": "200", "item_count": 2}],
            "selection_mode": "DIRECT",
        }
    ).price_bands[0]

    await PptPlanAgentRunner(provider, settings=settings).select_direct_candidates(
        1, band, candidates, item_count=2, scene_context="客户原始需求：户外活动"
    )

    assessment_payloads = [
        json.loads(call["user_prompt"])
        for call in provider.calls
        if call["response_model"] is PptCandidateAssessmentList
    ]
    assert len(assessment_payloads) == 3
    assert provider.max_active_assessments == 2
    assert sum(len(payload["candidates"]) for payload in assessment_payloads) == len(candidates)
    assert all(len(payload["candidates"]) <= 80 for payload in assessment_payloads)
    compact_row = next(
        row
        for payload in assessment_payloads
        for row in payload["candidates"]
        if row["specification"]
    )
    assert len(compact_row["specification"]) <= 60
    assert len(compact_row["selling_points"]) <= 72
    final_payload = next(
        json.loads(call["user_prompt"])
        for call in provider.calls
        if call["response_model"] is PptDirectSelectionProposal
    )
    full_row = next(
        row for row in final_payload["candidates"] if row["specification"] == full_specification
    )
    assert full_row["selling_points"] == full_selling_points
