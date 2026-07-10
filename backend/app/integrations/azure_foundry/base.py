"""AI model client interface (Layer 4).

The task executor talks to this interface only. Azure AI Foundry implements
it for production (Azure-hosted models exclusively — never an external or
ungoverned endpoint, LD-24); a deterministic mock serves development and CI
until the LD-23/24 West Europe deployment verification unlocks the live
backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    token_input: int | None
    token_output: int | None


class ModelClientError(Exception):
    """Model call failed. Message must be safe to log and store."""


class ModelClient(ABC):
    @abstractmethod
    async def complete(self, *, model: str, system: str, prompt: str) -> ModelResponse:
        """Run one completion; raise ModelClientError on failure."""
