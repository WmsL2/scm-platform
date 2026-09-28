from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

StructuredResult = TypeVar("StructuredResult", bound=BaseModel)


class KimiConfigurationError(RuntimeError):
    """Raised when the deployment has not configured the required Kimi capability."""


class KimiProviderError(RuntimeError):
    """Safe provider failure that never includes credentials or raw response bodies."""


class KimiStructuredOutputError(KimiProviderError):
    def __init__(self, response_model_name: str, safe_validation_summary: str) -> None:
        self.response_model_name = response_model_name
        self.safe_validation_summary = safe_validation_summary
        super().__init__(f"Kimi 返回的 {response_model_name} 结构不符合业务约束")


@dataclass(frozen=True)
class KimiPptArtifact:
    session_id: str
    artifact_id: str
    filename: str
    content: bytes


class KimiClient:
    """OpenAI-compatible Kimi inference adapter used only for controlled selection."""

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
        return "kimi"

    @property
    def model(self) -> str:
        return self.settings.kimi_model

    @property
    def prompt_version(self) -> str:
        return self.settings.kimi_prompt_version

    async def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredResult],
    ) -> StructuredResult:
        api_key = self._api_key()
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
            "max_tokens": self.settings.kimi_max_tokens,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.kimi_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self.settings.kimi_base_url.rstrip('/')}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise KimiProviderError("Kimi 选品请求失败，请稍后重试") from exc
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            summary = "; ".join(
                ".".join(str(part) for part in error["loc"])
                + f": {error['type']}: {error['msg']}"
                for error in exc.errors(include_input=False, include_url=False)
            )
            raise KimiStructuredOutputError(response_model.__name__, summary) from exc

    async def generate_ppt(
        self,
        *,
        title: str,
        instruction: str,
        source_path: Path,
        template_path: Path | None,
    ) -> KimiPptArtifact:
        """Run the hosted PPT Agent and return its first PPTX artifact."""

        api_key = self._api_key()
        agent_id = self.settings.kimi_ppt_agent_id
        environment_id = self.settings.kimi_environment_id
        if not agent_id or not environment_id:
            raise KimiConfigurationError(
                "Kimi PPT Agent 未配置，请设置 KIMI_PPT_AGENT_ID 和 KIMI_ENVIRONMENT_ID"
            )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "kimi-api-version": self.settings.kimi_hosted_api_version,
        }
        timeout = httpx.Timeout(self.settings.kimi_timeout_seconds)
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.kimi_base_url.rstrip("/"),
                headers=headers,
                timeout=timeout,
                transport=self._transport,
            ) as client:
                resource_ids = [await self._upload_file(client, source_path)]
                if template_path is not None:
                    resource_ids.append(await self._upload_file(client, template_path))
                session_response = await client.post(
                    "/v1/sessions",
                    json={
                        "agent_id": agent_id,
                        "environment_id": environment_id,
                        "title": title,
                        "resources": [
                            {"type": "file", "file_id": file_id} for file_id in resource_ids
                        ],
                    },
                )
                session_response.raise_for_status()
                session_id = str(session_response.json()["id"])
                event_response = await client.post(
                    f"/v1/sessions/{session_id}/events",
                    json={
                        "events": [
                            {
                                "type": "user.message",
                                "data": {"content": [{"type": "text", "text": instruction}]},
                            }
                        ]
                    },
                )
                event_response.raise_for_status()
                await self._wait_for_idle(client, session_id)
                artifacts_response = await client.get(
                    "/v1/artifacts", params={"session_id": session_id}
                )
                artifacts_response.raise_for_status()
                items = artifacts_response.json().get("items", [])
                pptx = next(
                    (
                        item
                        for item in items
                        if str(item.get("name") or item.get("filename") or "")
                        .lower()
                        .endswith(".pptx")
                    ),
                    None,
                )
                if pptx is None:
                    raise KimiProviderError("Kimi PPT Agent 未返回可下载的 PPTX 文件")
                artifact_id = str(pptx["id"])
                content_response = await client.get(f"/v1/artifacts/{artifact_id}/content")
                content_response.raise_for_status()
                return KimiPptArtifact(
                    session_id=session_id,
                    artifact_id=artifact_id,
                    filename=Path(str(pptx.get("name") or "方案.pptx")).name,
                    content=content_response.content,
                )
        except KimiProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise KimiProviderError("Kimi PPT 生成失败，请稍后重试") from exc

    async def _wait_for_idle(self, client: httpx.AsyncClient, session_id: str) -> None:
        deadline = time.monotonic() + self.settings.kimi_ppt_timeout_seconds
        while time.monotonic() < deadline:
            response = await client.get(f"/v1/sessions/{session_id}")
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            status = str(body.get("status", "")).lower()
            if status == "idle":
                return
            if status in {"failed", "error", "terminated"}:
                raise KimiProviderError("Kimi PPT 生成任务执行失败")
            await asyncio.sleep(self.settings.kimi_ppt_poll_seconds)
        raise KimiProviderError("Kimi PPT 生成超时，请稍后重试")

    @staticmethod
    async def _upload_file(client: httpx.AsyncClient, path: Path) -> str:
        with path.open("rb") as source:
            response = await client.post(
                "/v1/files",
                files={"file": (path.name, source, "application/octet-stream")},
            )
        response.raise_for_status()
        return str(response.json()["id"])

    def _api_key(self) -> str:
        if self.settings.kimi_api_key is None:
            raise KimiConfigurationError("Kimi 未配置，请设置 KIMI_API_KEY 后重试")
        return self.settings.kimi_api_key.get_secret_value()
