"""AzureFoundryClient unit tests — offline, transport mocked.

The live path is exercised by the golden set with AI_BACKEND=azure_foundry;
these tests pin request shape, auth header, and error handling.
"""

import httpx
import pytest

from app.integrations.azure_foundry.base import ModelClientError
from app.integrations.azure_foundry.client import AzureFoundryClient


@pytest.fixture
def foundry_env(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "foundry_endpoint", "https://unit.test.endpoint")
    monkeypatch.setattr(settings, "foundry_api_version", "2024-10-21")
    monkeypatch.setenv("FOUNDRY_API_KEY", "unit-test-key")
    return settings


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _patch_transport(monkeypatch, handler):
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _transport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


async def test_complete_parses_response_and_sends_auth(foundry_env, monkeypatch) -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("api-key")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Draft text [ref:case:1]."}}],
                "usage": {"prompt_tokens": 321, "completion_tokens": 45},
            },
        )

    _patch_transport(monkeypatch, handler)
    response = await AzureFoundryClient().complete(
        model="gpt-5-4", system="sys", prompt="user prompt"
    )
    assert response.text == "Draft text [ref:case:1]."
    assert response.model == "gpt-5-4"
    assert (response.token_input, response.token_output) == (321, 45)
    assert "/openai/deployments/gpt-5-4/chat/completions" in captured["url"]
    assert "api-version=2024-10-21" in captured["url"]
    assert captured["api_key"] == "unit-test-key"


async def test_http_error_becomes_model_client_error(foundry_env, monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": "RateLimited"}})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ModelClientError, match="429"):
        await AzureFoundryClient().complete(model="gpt-5-4", system="s", prompt="p")


async def test_malformed_body_becomes_model_client_error(foundry_env, monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ModelClientError, match="missing message content"):
        await AzureFoundryClient().complete(model="gpt-5-4", system="s", prompt="p")


async def test_missing_secret_becomes_model_client_error(foundry_env, monkeypatch) -> None:
    monkeypatch.delenv("FOUNDRY_API_KEY", raising=False)
    with pytest.raises(ModelClientError, match="credential unavailable"):
        await AzureFoundryClient().complete(model="gpt-5-4", system="s", prompt="p")


async def test_missing_endpoint_rejected(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "foundry_endpoint", "")
    with pytest.raises(ModelClientError, match="not configured"):
        await AzureFoundryClient().complete(model="gpt-5-4", system="s", prompt="p")