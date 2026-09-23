import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.integrations.deepseek.client import (
    DeepSeekClient,
    DeepSeekConfigurationError,
    DeepSeekProviderError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_schemas import CandidateRanking


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
            json={"choices": [{"message": {"content": '```json\n{"value":"ok"}\n```'}}]},
        )

    client = DeepSeekClient(
        settings(
            deepseek_base_url="https://provider.example/v1",
            deepseek_model="deepseek-reasoner",
        ),
        transport=httpx.MockTransport(handler),
    )

    assert (
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=Answer
        )
    ).value == "ok"


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "error_kind", "summary_part"),
    [
        ("not-json", "INVALID_JSON", "json_invalid"),
        (
            json.dumps(
                {
                    "candidates": [
                        {
                            "product_id": "00000000-0000-0000-0000-000000000001",
                            "score": 101,
                            "reason": "x",
                        }
                    ]
                }
            ),
            "SCHEMA_VALIDATION",
            "less_than_equal",
        ),
        (
            json.dumps(
                {
                    "candidates": [
                        {"product_id": "00000000-0000-0000-0000-000000000001", "score": 90}
                    ]
                }
            ),
            "SCHEMA_VALIDATION",
            "missing",
        ),
        (
            json.dumps(
                {
                    "candidates": [
                        {
                            "product_id": "00000000-0000-0000-0000-000000000001",
                            "score": 90,
                            "reason": "x",
                            "extra": True,
                        }
                    ]
                }
            ),
            "SCHEMA_VALIDATION",
            "extra_forbidden",
        ),
    ],
)
async def test_structured_validation_errors_are_diagnostic_and_redacted(
    content: str, error_kind: str, summary_part: str
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = DeepSeekClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(DeepSeekStructuredOutputError) as error:
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=CandidateRanking
        )
    assert error.value.response_model_name == "CandidateRanking"
    assert error.value.error_kind == error_kind
    assert summary_part in error.value.safe_validation_summary
    assert "00000000-0000" not in error.value.safe_validation_summary


@pytest.mark.asyncio
async def test_candidate_ranking_over_thirty_is_schema_validation_error() -> None:
    content = json.dumps(
        {
            "candidates": [
                {
                    "product_id": f"00000000-0000-0000-0000-{index:012d}",
                    "score": 90,
                    "reason": "合法原因",
                }
                for index in range(1, 32)
            ]
        }
    )

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = DeepSeekClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(DeepSeekStructuredOutputError) as error:
        await client.structured_completion(
            system_prompt="system", user_prompt="user", response_model=CandidateRanking
        )
    assert error.value.error_kind == "SCHEMA_VALIDATION"
    assert "too_long" in error.value.safe_validation_summary
