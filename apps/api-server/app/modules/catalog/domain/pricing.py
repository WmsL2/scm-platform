"""Deterministic Product Pricing domain rules."""

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

_SCALE = Decimal("0.0001")
_MARKET_PRICE_INCREMENT = Decimal("10")
_AGREEMENT_PRICE_MULTIPLIER = Decimal("1.2")
_ONE = Decimal("1")


class PricingCalculationError(ValueError):
    """Raised when frozen pricing rules cannot produce a valid result."""


@dataclass(frozen=True, slots=True)
class PricingResult:
    """System-calculated four-decimal Product pricing values."""

    market_price: Decimal
    agreement_price: Decimal
    agreement_purchase_price: Decimal
    profit: Decimal
    jd_margin: Decimal
    deduction_review: Decimal
    gross_margin: Decimal
    discount_rate: Decimal
    price_inflation_rate: Decimal


def calculate_product_pricing(
    *,
    cost_price: Decimal,
    jd_price: Decimal,
    jd_self_operated_price: Decimal,
    deduction_rate: Decimal,
) -> PricingResult:
    """Calculate deterministic System Calculated Values using Decimal only.

    Every derived value is quantized to the official four-decimal scale before
    it is used by a downstream formula. The only rounding exception is
    ``deduction_review``, which truncates toward zero.

    This service does not decide whether Excel source values are adopted, how
    pricing differences are handled, or whether an import is confirmed. A
    later Product Import responsibility compares Excel Derived Values with
    these System Calculated Values and applies reconciliation policy; this
    function does not decide which value is stored by the formal Product.
    """

    _require_decimal(
        cost_price=cost_price,
        jd_price=jd_price,
        jd_self_operated_price=jd_self_operated_price,
        deduction_rate=deduction_rate,
    )

    market_price = _half_up(jd_price + _MARKET_PRICE_INCREMENT)
    agreement_price = _half_up(cost_price * _AGREEMENT_PRICE_MULTIPLIER)

    if jd_price == Decimal("0"):
        raise PricingCalculationError("jd_price must not be zero")
    if agreement_price == Decimal("0"):
        raise PricingCalculationError("agreement_price must not be zero")
    if jd_self_operated_price == Decimal("0"):
        raise PricingCalculationError("jd_self_operated_price must not be zero")

    agreement_purchase_price = _half_up(agreement_price * (_ONE - deduction_rate))
    profit = _half_up(agreement_purchase_price - cost_price)
    jd_margin = _half_up((jd_price - agreement_purchase_price) / jd_price)
    deduction_review = _down((agreement_price - agreement_purchase_price) / agreement_price)
    gross_margin = _half_up(profit / agreement_price)
    discount_rate = _half_up(agreement_price / jd_self_operated_price)
    price_inflation_rate = _half_up(
        (agreement_price - jd_self_operated_price) / jd_self_operated_price
    )

    return PricingResult(
        market_price=market_price,
        agreement_price=agreement_price,
        agreement_purchase_price=agreement_purchase_price,
        profit=profit,
        jd_margin=jd_margin,
        deduction_review=deduction_review,
        gross_margin=gross_margin,
        discount_rate=discount_rate,
        price_inflation_rate=price_inflation_rate,
    )


def _require_decimal(**values: Decimal) -> None:
    for name, value in values.items():
        if not isinstance(value, Decimal):
            raise TypeError(f"{name} must be a Decimal")
        if not value.is_finite():
            raise PricingCalculationError(f"{name} must be finite")


def _half_up(value: Decimal) -> Decimal:
    return value.quantize(_SCALE, rounding=ROUND_HALF_UP)


def _down(value: Decimal) -> Decimal:
    return value.quantize(_SCALE, rounding=ROUND_DOWN)
