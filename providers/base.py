from abc import ABC, abstractmethod

MAX_OUTPUT_TOKENS = 50_000


class ModelProvider(ABC):
    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> str:
        """Send a system + user prompt, return the raw text response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name shown in the UI."""
        ...
