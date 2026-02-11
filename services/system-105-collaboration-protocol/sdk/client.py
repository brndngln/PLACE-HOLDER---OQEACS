"""SDK client placeholder for collaboration-protocol."""

from dataclasses import dataclass


@dataclass
class System105Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
