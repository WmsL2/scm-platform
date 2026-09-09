from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.modules.catalog.domain.pricing import (
    PricingCalculationError,
    calculate_product_pricing,
)


def test_calculates_pricing_for_five_percent_deduction_rate() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("100"),
        jd_price=Decimal("200"),
        jd_self_operated_price=Decimal("250"),
        deduction_rate=Decimal("0.0500"),
    )

    assert result.market_price == Decimal("210.0000")
    assert result.agreement_price == Decimal("120.0000")
    assert result.agreement_purchase_price == Decimal("114.0000")
    assert result.profit == Decimal("14.0000")
    assert result.jd_margin == Decimal("0.4300")
    assert result.deduction_review == Decimal("0.0500")
    assert result.gross_margin == Decimal("0.1167")
    assert result.discount_rate == Decimal("0.4800")
    assert result.price_inflation_rate == Decimal("-0.5200")


def test_calculates_pricing_for_eight_percent_deduction_rate() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("100"),
        jd_price=Decimal("200"),
        jd_self_operated_price=Decimal("250"),
        deduction_rate=Decimal("0.0800"),
    )

    assert result.agreement_purchase_price == Decimal("110.4000")
    assert result.profit == Decimal("10.4000")
    assert result.jd_margin == Decimal("0.4480")
    assert result.deduction_review == Decimal("0.0800")
    assert result.gross_margin == Decimal("0.0867")


def test_ordinary_values_use_round_half_up_at_the_fourth_decimal() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("1"),
        jd_price=Decimal("1.23445"),
        jd_self_operated_price=Decimal("2"),
        deduction_rate=Decimal("0.0500"),
    )

    assert result.market_price == Decimal("11.2345")


def test_deduction_review_uses_round_down_at_the_fourth_decimal() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("0.41725"),
        jd_price=Decimal("1"),
        jd_self_operated_price=Decimal("1"),
        deduction_rate=Decimal("0.0800"),
    )

    assert result.agreement_price == Decimal("0.5007")
    assert result.agreement_purchase_price == Decimal("0.4606")
    assert result.deduction_review == Decimal("0.0800")
    assert Decimal("0.0800878769").quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ) == Decimal("0.0801")


def test_downstream_calculation_uses_quantized_agreement_price() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("1.0287083333334"),
        jd_price=Decimal("2"),
        jd_self_operated_price=Decimal("2"),
        deduction_rate=Decimal("0.0500"),
    )

    assert result.agreement_price == Decimal("1.2345")
    assert result.agreement_purchase_price == Decimal("1.1728")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("jd_price", Decimal("0"), "jd_price must not be zero"),
        ("cost_price", Decimal("0"), "agreement_price must not be zero"),
        (
            "jd_self_operated_price",
            Decimal("0"),
            "jd_self_operated_price must not be zero",
        ),
    ],
)
def test_rejects_zero_denominators(field: str, value: Decimal, message: str) -> None:
    values: dict[str, Decimal] = {
        "cost_price": Decimal("100"),
        "jd_price": Decimal("200"),
        "jd_self_operated_price": Decimal("250"),
        "deduction_rate": Decimal("0.0500"),
    }
    values[field] = value

    with pytest.raises(PricingCalculationError, match=message):
        calculate_product_pricing(**values)


@pytest.mark.parametrize("invalid_value", ["100", 100.0])
def test_rejects_non_decimal_inputs(invalid_value: object) -> None:
    with pytest.raises(TypeError, match="cost_price must be a Decimal"):
        calculate_product_pricing(
            cost_price=invalid_value,  # type: ignore[arg-type]
            jd_price=Decimal("200"),
            jd_self_operated_price=Decimal("250"),
            deduction_rate=Decimal("0.0500"),
        )


def test_outputs_are_decimals_at_the_official_four_decimal_scale() -> None:
    result = calculate_product_pricing(
        cost_price=Decimal("100"),
        jd_price=Decimal("200"),
        jd_self_operated_price=Decimal("250"),
        deduction_rate=Decimal("0.0500"),
    )

    for field in result.__dataclass_fields__:
        value = getattr(result, field)
        assert isinstance(value, Decimal)
        assert value.as_tuple().exponent == -4
