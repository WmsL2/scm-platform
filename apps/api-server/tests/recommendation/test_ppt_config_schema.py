from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.recommendation.ppt_schemas import PptRecommendationConfigUpdateRequest


def _payload(bands: list[dict[str, object]]) -> dict[str, object]:
    return {"recommendation_mode": "SINGLE", "price_bands": bands, "fulfillment_deadline": None}


def test_price_band_schema_accepts_a_single_point_band() -> None:
    config = PptRecommendationConfigUpdateRequest.model_validate(
        _payload([{"min_price": "88", "max_price": "88", "item_count": 1}])
    )

    assert config.price_bands[0].min_price == Decimal("88")


@pytest.mark.parametrize(
    "band",
    [
        {"min_price": None, "max_price": "", "item_count": 1},
        {"min_price": "-1", "max_price": "10", "item_count": 1},
        {"min_price": "11", "max_price": "10", "item_count": 1},
        {"min_price": None, "max_price": "10", "item_count": 501},
    ],
)
def test_price_band_schema_rejects_invalid_values(band: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PptRecommendationConfigUpdateRequest.model_validate(_payload([band]))


def test_price_band_schema_rejects_overlapping_ranges() -> None:
    with pytest.raises(ValidationError, match="price bands must not overlap"):
        PptRecommendationConfigUpdateRequest.model_validate(
            _payload(
                [
                    {"min_price": "10", "max_price": "20", "item_count": 10},
                    {"min_price": "20", "max_price": "30", "item_count": 10},
                ]
            )
        )
