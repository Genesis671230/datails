"""Azure AI Foundry model client (LD-24).

Calls the Azure OpenAI-compatible chat-completions API on the Datails
Foundry instance. Model names passed in are the Foundry DEPLOYMENT names
(see services/ai/model_router.py). Auth: API key resolved through the
secret resolver (env var locally, Key Vault in Azure); managed identity
replaces the key at the Container Apps deploy.

Never any external or ungoverned endpoint — the endpoint is the tenant's
regional Foundry instance, full stop.
"""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.azure_foundry.base import ModelClient, ModelClientError, ModelResponse
from app.integrations.key_vault.base import SecretResolutionError

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 120


class AzureFoundryClient(ModelClient):
    async def complete(self, *, model: str, system: str, prompt: str) -> ModelResponse:
        settings = get_settings()
        if not settings.foundry_endpoint:
            raise ModelClientError("FOUNDRY_ENDPOINT is not configured")

        from app.integrations.factories import get_secret_resolver

        try:
            api_key = await get_secret_resolver().get_secret(settings.foundry_secret_ref)
        except SecretResolutionError as exc:
            raise ModelClientError(f"Foundry credential unavailable: {exc}") from exc

        url = (
            f"{settings.foundry_endpoint.rstrip('/')}/openai/deployments/"
            f"{model}/chat/completions"
        )
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    params={"api-version": settings.foundry_api_version},
                    headers={"api-key": api_key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ModelClientError(f"Foundry request failed: {exc}") from exc

        if response.status_code != 200:
            # Bodies can carry vendor error details; never echo the key.
            raise ModelClientError(
                f"Foundry returned {response.status_code}: {response.text[:300]}"
            )

        body = response.json()
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelClientError("Foundry response missing message content") from exc
        usage = body.get("usage", {})
        return ModelResponse(
            text=text or "",
            model=model,
            token_input=usage.get("prompt_tokens"),
            token_output=usage.get("completion_tokens"),
        )
