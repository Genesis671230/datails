"""Deterministic mock model client for development and CI.

Produces structured, source-citing draft text derived from the prompt so
golden-set assertions are stable. Never used outside ENVIRONMENT=local/CI —
the factory refuses the mock backend elsewhere.
"""

from app.integrations.azure_foundry.base import ModelClient, ModelClientError, ModelResponse

CHARS_PER_TOKEN = 4


class MockModelClient(ModelClient):
    async def complete(self, *, model: str, system: str, prompt: str) -> ModelResponse:
        if "SIMULATE_MODEL_FAILURE" in prompt:
            raise ModelClientError("mock model simulated failure")
        # Echo the grounded context headers so tests can assert the draft is
        # case-grounded; real drafting quality arrives with the live backend.
        section_names = [
            line.removeprefix("## ").strip()
            for line in prompt.splitlines()
            if line.startswith("## ")
        ]
        text = (
            f"[mock:{model}] Draft grounded in case context.\n"
            f"Sections used: {', '.join(section_names) or 'none'}.\n"
            "All statements cite the source references provided in context."
        )
        return ModelResponse(
            text=text,
            model=model,
            token_input=len(prompt) // CHARS_PER_TOKEN,
            token_output=len(text) // CHARS_PER_TOKEN,
        )
