"""SDK client placeholder for webhook-relay."""

from dataclasses import dataclass


@dataclass
class System130Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
