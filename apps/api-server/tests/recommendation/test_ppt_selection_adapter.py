from __future__ import annotations

from decimal import Decimal

from app.modules.recommendation.application.agent_schemas import RequirementAnalysis
from app.modules.recommendation.application.ppt_selection_adapter import (
    PptSelectionServiceTools,
)


def test_type5_price_bands_override_requirement_budget_and_agreement_price() -> None:
    analysis = RequirementAnalysis(
        summary="会员慰问品",
        keywords=["慰问品"],
        budget_min=Decimal("100"),
        budget_max=Decimal("500"),
        agreement_price_min=Decimal("100"),
        agreement_price_max=Decimal("500"),
        jd_price_min=Decimal("80"),
        jd_price_max=Decimal("200"),
        gross_margin_min=Decimal("0.08"),
        discount_rate_max=Decimal("0.9"),
    )

    requirement = PptSelectionServiceTools._parsed_requirement(analysis)

    assert requirement.agreement_price_min is None
    assert requirement.agreement_price_max is None
    assert requirement.jd_price_min == Decimal("80")
    assert requirement.jd_price_max == Decimal("200")
    assert requirement.gross_margin_min == Decimal("0.08")
    assert requirement.discount_rate_max == Decimal("0.9")
