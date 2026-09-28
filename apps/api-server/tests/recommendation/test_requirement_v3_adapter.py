from __future__ import annotations

from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest

from app.modules.recommendation.application.agent_schemas import RequirementAnalysis
from app.modules.recommendation.application.agent_service_adapter import RecommendationServiceTools
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import ParsedRequirement


class _ServiceStub:
    def __init__(self) -> None:
        self.requirement: ParsedRequirement | None = None

    async def begin_analysis(self, _: object) -> None:
        return None

    async def save_parsed_requirement(
        self, _: object, requirement: ParsedRequirement, **__: str
    ) -> None:
        self.requirement = requirement


@pytest.mark.asyncio
async def test_default_budget_maps_to_agreement_price_and_explicit_jd_stays_jd() -> None:
    stub = _ServiceStub()
    tools = RecommendationServiceTools(
        uuid4(),
        cast(RecommendationService, stub),
        provider="test",
        model="test",
        prompt_version="v3",
    )
    await tools.prepare(
        RequirementAnalysis(
            summary="小家电，预算200元以内，京东价300元以内，点位6%以上，折扣率8折以内",
            keywords=["小家电"],
            budget_max=Decimal("200"),
            jd_price_max=Decimal("300"),
            gross_margin_min=Decimal("0.06"),
            discount_rate_max=Decimal("0.8"),
        )
    )
    assert stub.requirement is not None
    assert stub.requirement.agreement_price_max == Decimal("200")
    assert stub.requirement.jd_price_max == Decimal("300")
    assert stub.requirement.gross_margin_min == Decimal("0.06")
    assert stub.requirement.discount_rate_max == Decimal("0.8")
