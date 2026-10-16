from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ProductSelectionScope:
    """A deterministic project/run boundary for product-master candidate recall."""

    company_names: tuple[str, ...] = ()
    purchasing_agents: tuple[str, ...] = ()

    @classmethod
    def from_values(
        cls,
        company_names: Sequence[str] | None,
        purchasing_agents: Sequence[str] | None,
    ) -> "ProductSelectionScope":
        return cls(
            company_names=cls._normalize(company_names),
            purchasing_agents=cls._normalize(purchasing_agents),
        )

    @classmethod
    def from_snapshot(cls, value: Mapping[str, object] | None) -> "ProductSelectionScope":
        if value is None:
            return cls()
        return cls.from_values(
            cls._strings(value.get("company_names")),
            cls._strings(value.get("purchasing_agents")),
        )

    def snapshot(self) -> dict[str, list[str]]:
        return {
            "company_names": list(self.company_names),
            "purchasing_agents": list(self.purchasing_agents),
        }

    @staticmethod
    def _strings(value: object) -> Sequence[str] | None:
        return value if isinstance(value, (list, tuple)) else None

    @staticmethod
    def _normalize(values: Sequence[str] | None) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw_value in values or ():
            if not isinstance(raw_value, str):
                continue
            value = raw_value.strip()
            if value and value not in normalized:
                normalized.append(value)
        return tuple(normalized)
