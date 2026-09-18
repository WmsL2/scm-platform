import base64
import binascii
import json
from dataclasses import dataclass
from typing import Literal, cast

CategoryFilterLevel = Literal["LEVEL1", "LEVEL2", "LEVEL3"]


@dataclass(frozen=True)
class ProductCategorySelection:
    level: CategoryFilterLevel
    path: tuple[str, ...]


def selection_key(level: CategoryFilterLevel, path: tuple[str, ...]) -> str:
    expected_length = int(level[-1])
    if len(path) != expected_length or any(not value for value in path):
        raise ValueError("invalid product category path")
    encoded = (
        base64.urlsafe_b64encode(
            json.dumps(path, ensure_ascii=False, separators=(",", ":")).encode()
        )
        .decode()
        .rstrip("=")
    )
    return f"{level}:{encoded}"


def parse_selection(value: str) -> ProductCategorySelection:
    level, separator, encoded = value.partition(":")
    if level not in {"LEVEL1", "LEVEL2", "LEVEL3"} or not separator or not encoded:
        raise ValueError("invalid product category selection")
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded).decode())
    except (binascii.Error, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid product category selection") from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) and item for item in decoded):
        raise ValueError("invalid product category selection")
    path = tuple(decoded)
    category_level = cast(CategoryFilterLevel, level)
    if len(path) != int(category_level[-1]):
        raise ValueError("invalid product category selection")
    return ProductCategorySelection(level=category_level, path=path)
