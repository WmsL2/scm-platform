import json
import logging
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)
_FENCED_JSON = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
logger = logging.getLogger(__name__)
_request_telemetry: ContextVar["DeepSeekRequestTelemetry | None"] = ContextVar(
    "deepseek_request_telemetry", default=None
)


@dataclass
class DeepSeekRequestTelemetry:
    """Per-request usage data, isolated across concurrent asyncio tasks."""

    label: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    provider_duration_ms: int | None = None


@contextmanager
def capture_deepseek_request_telemetry(
    telemetry: DeepSeekRequestTelemetry,
) -> Iterator[DeepSeekRequestTelemetry]:
    token = _request_telemetry.set(telemetry)
    try:
        yield telemetry
    finally:
        _request_telemetry.reset(token)


class DeepSeekConfigurationError(RuntimeError):
    """Raised when the provider is intentionally not configured yet."""


class DeepSeekProviderError(RuntimeError):
    """Provider failure safe to surface without leaking credentials or response bodies."""

    def __init__(
        self, message: str, *, error_kind: str = "PROVIDER_ERROR", retryable: bool = True
    ) -> None:
        self.error_kind = error_kind
        self.retryable = retryable
        super().__init__(message)


class DeepSeekStructuredOutputError(DeepSeekProviderError):
    """A safe, actionable failure while parsing a structured provider response."""

    def __init__(
        self,
        *,
        response_model_name: str,
        safe_validation_summary: str,
        error_kind: str,
    ) -> None:
        self.response_model_name = response_model_name
        self.safe_validation_summary = safe_validation_summary
        self.error_kind = error_kind
        super().__init__(
            f"DeepSeek 返回的 {response_model_name} 结构不符合业务约束",
            error_kind=error_kind,
            retryable=False,
        )


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
        max_tokens: int | None = None,
    ) -> StructuredResult:
        api_key = self.settings.deepseek_api_key
        if api_key is None:
            raise DeepSeekConfigurationError("DeepSeek 未配置，请设置 DEEPSEEK_API_KEY 后重试")
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
            "max_tokens": max_tokens or self.settings.deepseek_max_tokens,
        }
        url = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        request_started = perf_counter()
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
                if response.status_code >= 400:
                    # Do not log or expose the body: it can contain request echoes.
                    kind = (
                        "CONTEXT_LENGTH_EXCEEDED"
                        if response.status_code == 400
                        else f"HTTP_{response.status_code}"
                    )
                    retryable = response.status_code in {408, 429} or response.status_code >= 500
                    message = (
                        "DeepSeek 输入超过上下文限制，请缩小任务后重试"
                        if kind == "CONTEXT_LENGTH_EXCEEDED"
                        else "DeepSeek 请求失败，请稍后重试"
                    )
                    raise DeepSeekProviderError(message, error_kind=kind, retryable=retryable)
                body = response.json()
        except DeepSeekProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise DeepSeekProviderError(
                "DeepSeek 请求超时，请稍后重试", error_kind="TIMEOUT"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise DeepSeekProviderError("DeepSeek 请求失败，请稍后重试") from exc

        telemetry = _request_telemetry.get()
        if telemetry is not None:
            telemetry.provider_duration_ms = round((perf_counter() - request_started) * 1000)
        usage = body.get("usage") if isinstance(body, dict) else None
        if isinstance(usage, dict):
            if telemetry is not None:
                telemetry.prompt_tokens = self._int_or_none(usage.get("prompt_tokens"))
                telemetry.completion_tokens = self._int_or_none(usage.get("completion_tokens"))
                telemetry.total_tokens = self._int_or_none(usage.get("total_tokens"))
            logger.info(
                "deepseek structured usage model=%s label=%s prompt=%s completion=%s "
                "total=%s duration_ms=%s",
                self.model,
                telemetry.label if telemetry else None,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
                telemetry.provider_duration_ms if telemetry else None,
            )

        try:
            choice = body["choices"][0]
            finish_reason = choice.get("finish_reason")
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekStructuredOutputError(
                response_model_name=response_model.__name__,
                safe_validation_summary=(
                    "content: missing_content: Provider response has no text content"
                ),
                error_kind="MISSING_CONTENT",
            ) from exc

        if finish_reason == "length":
            raise DeepSeekStructuredOutputError(
                response_model_name=response_model.__name__,
                safe_validation_summary="content: output_truncated: finish_reason=length",
                error_kind="OUTPUT_TRUNCATED",
            )

        try:
            normalized_content = self._strip_json_fence(content)
            json.loads(normalized_content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekStructuredOutputError(
                response_model_name=response_model.__name__,
                safe_validation_summary="content: json_invalid: JSON decode failed",
                error_kind="INVALID_JSON",
            ) from exc
        try:
            return response_model.model_validate_json(normalized_content)
        except ValidationError as exc:
            raise DeepSeekStructuredOutputError(
                response_model_name=response_model.__name__,
                safe_validation_summary=self._safe_validation_summary(exc),
                error_kind="SCHEMA_VALIDATION",
            ) from exc

    @staticmethod
    def _strip_json_fence(content: Any) -> str:
        if not isinstance(content, str):
            raise TypeError("provider content must be text")
        value = content.strip()
        match = _FENCED_JSON.fullmatch(value)
        return match.group(1) if match else value

    @staticmethod
    def _safe_validation_summary(exc: ValidationError) -> str:
        """Expose only location, type and message; never Pydantic's input value."""
        return "; ".join(
            ".".join(str(part) for part in error["loc"]) + f": {error['type']}: {error['msg']}"
            for error in exc.errors(include_input=False, include_url=False)
        )

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        return value if isinstance(value, int) else None


def compact_json(items: Sequence[BaseModel | dict[str, Any]]) -> str:
    values = [
        item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in items
    ]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))
