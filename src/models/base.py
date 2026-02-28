"""Abstract base class for model callers."""

from abc import ABC, abstractmethod


class ModelCaller(ABC):
    """Abstract base for LLM API callers."""

    @abstractmethod
    async def call(
        self, prompt: str, system: str = "", temperature: float = 0.7
    ) -> str:
        """Send a prompt to the model and return the response text."""
        ...
