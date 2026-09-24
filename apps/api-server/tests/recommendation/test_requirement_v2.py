from decimal import Decimal

import pytest

from app.common.contracts import AppError
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.schemas import (
    ManualCheck,
    ManualCheckStatus,
    ManualCheckType,
    ManualCheckUpdateRequest,
    ParsedRequirement,
)


def test_requirement_v2_has_no_hidden_margin_and_separates_constraints() -> None:
    requirement = ParsedRequirement(
        gross_margin_min=Decimal("0.06"),
        explicit_category_keywords=[],
        category_intents=["中秋", "国庆"],
        preferred_brands=["华为"],
        promotion_preference="SPECIAL_PRICE",
        demand_mode="REDEMPTION",
        fulfillment_mode="DROP_SHIPPING",
        manual_checks=[
            ManualCheck(
                code=ManualCheckType.DROP_SHIPPING,
                label="是否支持一件代发",
                requirement_text="一件代发",
            )
        ],
    )
    assert requirement.gross_margin_min == Decimal("0.06")
    assert requirement.required_brands == []
    assert requirement.category_intents == ["中秋", "国庆"]
    assert requirement.manual_checks[0].status is ManualCheckStatus.PENDING
    assert ParsedRequirement().gross_margin_min is None


@pytest.mark.parametrize(
    ("status", "error_code"),
    [
        ("PENDING", "RECOMMENDATION_MANUAL_CHECK_PENDING"),
        ("FAIL", "RECOMMENDATION_MANUAL_CHECK_FAILED"),
    ],
)
def test_required_manual_checks_block_confirmation(status: str, error_code: str) -> None:
    candidate = RecommendationCandidate(
        manual_flags={
            "checks": [
                {
                    "code": "DROP_SHIPPING",
                    "label": "是否支持一件代发",
                    "requirement_text": "一件代发",
                    "required": True,
                    "status": status,
                    "evidence": None,
                }
            ]
        }
    )
    with pytest.raises(AppError) as exc_info:
        RecommendationService._ensure_manual_checks_pass(candidate)
    assert exc_info.value.code == error_code


def test_passed_or_legacy_manual_checks_do_not_block_confirmation() -> None:
    passed = RecommendationCandidate(
        manual_flags={"checks": [{"required": True, "status": "PASS"}]}
    )
    RecommendationService._ensure_manual_checks_pass(passed)
    RecommendationService._ensure_manual_checks_pass(RecommendationCandidate(manual_flags=None))


def test_manual_check_review_payload_cannot_change_server_contract() -> None:
    update = ManualCheckUpdateRequest(
        checks=[{"code": "DROP_SHIPPING", "status": "PASS", "evidence": "供应商确认"}]
    )
    assert update.checks[0].status is ManualCheckStatus.PASS
    with pytest.raises(Exception):
        ManualCheckUpdateRequest(
            checks=[
                {
                    "code": "DROP_SHIPPING",
                    "status": "PASS",
                    "required": False,
                }
            ]
        )
