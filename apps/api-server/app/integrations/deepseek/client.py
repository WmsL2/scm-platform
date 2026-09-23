import json
import re
from collections.abc import Sequence
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)
_FENCED_JSON = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


class DeepSeekConfigurationError(RuntimeError):
    """Raised when the provider is intentionally not configured yet."""


class DeepSeekProviderError(RuntimeError):
    """Provider failure safe to surface without leaking credentials or response bodies."""


class DeepSeekClient:
    """Small OpenAI-compatible DeepSeek adapter with strict structured-output validation."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport

    @property
    def provider(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return self.settings.deepseek_model

    @property
    def prompt_version(self) -> str:
        return self.settings.deepseek_prompt_version

    async def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredResult],
    ) -> StructuredResult:
        api_key = self.settings.deepseek_api_key
        if api_key is None:
            raise DeepSeekConfigurationError(
                "DeepSeek 未配置，请设置 DEEPSEEK_API_KEY 后重试"
            )
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\n必须严格符合以下 JSON Schema：{schema}",
                },
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": self.settings.deepseek_max_tokens,
        }
        url = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.deepseek_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key.get_secret_value()}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DeepSeekProviderError("DeepSeek 请求失败，请稍后重试") from exc

        try:
            content = body["choices"][0]["message"]["content"]
            return response_model.model_validate_json(self._strip_json_fence(content))
        except (KeyError, IndexError, TypeError, ValidationError, json.JSONDecodeError) as exc:
            raise DeepSeekProviderError("DeepSeek 返回的数据结构不符合业务约束") from exc

    @staticmethod
    def _strip_json_fence(content: Any) -> str:
        if not isinstance(content, str):
            raise TypeError("provider content must be text")
        value = content.strip()
        match = _FENCED_JSON.fullmatch(value)
        return match.group(1) if match else value


def compact_json(items: Sequence[BaseModel | dict[str, Any]]) -> str:
    values = [
        item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in items
    ]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))
