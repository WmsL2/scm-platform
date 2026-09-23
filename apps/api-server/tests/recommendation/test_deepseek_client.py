import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.deepseek.client import (
    DeepSeekClient,
    DeepSeekConfigurationError,
    DeepSeekProviderError,
)


class Answer(BaseModel):
    value: str


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "mysql+asyncmy://test:test@localhost/test",
        "auth_jwt_secret": "test-secret",
        "deepseek_api_key": "provider-secret",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_structured_completion_uses_config_and_validates_json() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://provider.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer provider-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "deepseek-reasoner"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "```json\n{\"value\":\"ok\"}\n```"}}]},
        )

    client = DeepSeekClient(
        settings(
            deepseek_base_url="https://provider.example/v1",
            deepseek_model="deepseek-reasoner",
        ),
        transport=httpx.MockTransport(handler),
    )

    assert (await client.structured_completion(
        system_prompt="system", user_prompt="user", response_model=Answer
    )).value == "ok"


@pytest.mark.asyncio
async def test_missing_key_does_not_make_network_request() -> None:
    client = DeepSeekClient(settings(deepseek_api_key=None))
    with pytest.raises(DeepSeekConfigurationError, match="DEEPSEEK_API_KEY"):
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=Answer
        )


@pytest.mark.asyncio
async def test_provider_error_never_exposes_response_or_secret() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="provider-secret internal-detail")

    client = DeepSeekClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(DeepSeekProviderError) as error:
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=Answer
        )
    assert "provider-secret" not in str(error.value)
    assert "internal-detail" not in str(error.value)
