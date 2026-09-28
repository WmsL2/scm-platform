import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.kimi.client import (
    KimiClient,
    KimiConfigurationError,
    KimiProviderError,
)


class Answer(BaseModel):
    value: str


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "mysql+asyncmy://test:test@localhost/test",
        "auth_jwt_secret": "test-secret",
        "kimi_api_key": "kimi-secret",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_structured_completion_uses_kimi_config_and_validates_json() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://provider.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer kimi-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "kimi-k2.5"
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"value":"ok"}'}}]})

    client = KimiClient(
        settings(kimi_base_url="https://provider.example"),
        transport=httpx.MockTransport(handler),
    )
    result = await client.structured_completion(
        system_prompt="system", user_prompt="user", response_model=Answer
    )
    assert result.value == "ok"


@pytest.mark.asyncio
async def test_missing_kimi_key_stops_before_network() -> None:
    client = KimiClient(settings(kimi_api_key=None))
    with pytest.raises(KimiConfigurationError, match="KIMI_API_KEY"):
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=Answer
        )


@pytest.mark.asyncio
async def test_kimi_provider_error_redacts_secret_and_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="kimi-secret internal-detail")

    client = KimiClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(KimiProviderError) as error:
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=Answer
        )
    assert "kimi-secret" not in str(error.value)
    assert "internal-detail" not in str(error.value)
