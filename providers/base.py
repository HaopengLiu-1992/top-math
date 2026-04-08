from abc import ABC, abstractmethod


class ModelProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        """Send a system + user prompt, return the raw text response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name shown in the UI."""
        ...
