from decimal import Decimal

import pytest

from app.modules.recommendation.schemas import ParsedRequirement


def test_requirement_v3_keeps_only_category_and_explicit_numeric_price_constraints() -> None:
    requirement = ParsedRequirement(
        requirement_version="v3",
        explicit_category_keywords=["食品饮料"],
        agreement_price_max=Decimal("200"),
        discount_rate_max=Decimal("0.8"),
        gross_margin_min=Decimal("0.06"),
        required_brands=["某品牌"],
        scenarios=["中秋"],
        fulfillment_mode="DROP_SHIPPING",
    )
    assert requirement.agreement_price_max == Decimal("200")
    assert requirement.discount_rate_max == Decimal("0.8")
    assert requirement.gross_margin_min == Decimal("0.06")
    assert requirement.required_brands == ["某品牌"]
    assert ParsedRequirement().gross_margin_min is None


@pytest.mark.parametrize(
    "values",
    [
        {"agreement_price_min": "201", "agreement_price_max": "200"},
        {"discount_rate_min": "0.9", "discount_rate_max": "0.8"},
        {"gross_margin_min": "0.07", "gross_margin_max": "0.06"},
    ],
)
def test_requirement_rejects_inverted_hard_price_ranges(values: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        ParsedRequirement(**values)


def test_historical_manual_json_remains_read_compatible_and_is_not_a_contract() -> None:
    requirement = ParsedRequirement.model_validate(
        {"manual_checks": [{"code": "DROP_SHIPPING", "status": "PENDING"}]}
    )
    assert requirement.manual_checks[0]["status"] == "PENDING"


def test_requirement_accepts_allocation_style_explicit_categories_without_quantity_limits() -> None:
    requirement = ParsedRequirement(
        requirement_version="v6",
        explicit_category_keywords=["家电", "厨具", "日用"],
        category_intents=["家电", "生活电器", "厨具", "厨房用品", "日用"],
    )

    assert requirement.explicit_category_keywords == ["家电", "厨具", "日用"]
    assert requirement.total_quota is None
