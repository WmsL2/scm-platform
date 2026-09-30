from __future__ import annotations

import uuid
from decimal import Decimal

from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
)


def _candidate(rank: int, agreement_price: str) -> RecommendationCandidate:
    return RecommendationCandidate(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        rank=rank,
        score=Decimal("90"),
        product_snapshot={"product_name": f"商品 {rank}"},
        supplier_snapshot={},
        price_snapshot={"agreement_price": agreement_price},
    )


def test_generated_mixed_plans_rotate_full_per_plan_product_sets() -> None:
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="MIXED",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=3,
        plan_count_per_band=3,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    plans = PptSolutionService._build_plans(
        config,
        [_candidate(1, "120"), _candidate(2, "130"), _candidate(3, "140"), _candidate(4, "150")],
    )

    assert [plan["plan_type"] for plan in plans] == ["SINGLE", "COMBINATION", "SINGLE"]
    assert all(len(plan["candidate_ids"]) == 3 for plan in plans)
    assert plans[0]["candidate_ids"] != plans[1]["candidate_ids"]
    assert plans[1]["candidate_ids"] != plans[2]["candidate_ids"]


def test_plan_is_not_created_when_the_price_band_has_too_few_products() -> None:
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=50,
        plan_count_per_band=6,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    plans = PptSolutionService._build_plans(
        config,
        [_candidate(index, "120") for index in range(1, 21)],
    )

    assert plans == []


def test_each_plan_uses_requested_quantity_from_full_pool_with_overlap() -> None:
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "100", "max_price": "200"}],
        candidate_count_per_band=50,
        plan_count_per_band=6,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    plans = PptSolutionService._build_plans(
        config,
        [_candidate(index, "120") for index in range(1, 71)],
    )

    assert len(plans) == 6
    assert all(len(plan["candidate_ids"]) == 50 for plan in plans)
    assert len({tuple(plan["candidate_ids"]) for plan in plans}) == 6


def test_price_band_availability_reports_the_actual_frozen_candidate_count() -> None:
    config = PptRecommendationConfig(
        project_id=uuid.uuid4(),
        recommendation_mode="SINGLE",
        price_bands=[{"min_price": "0", "max_price": "500"}],
        candidate_count_per_band=200,
        plan_count_per_band=6,
        fulfillment_deadline=None,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )

    availability = PptSolutionService._plan_availability(
        config, [_candidate(index, "120") for index in range(1, 201)]
    )

    assert availability[0].candidate_count == 200
    assert availability[0].can_generate is True
    assert "满足每方案 200 件" in availability[0].message
